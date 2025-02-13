import json
import traceback
from typing import List, Dict
import openai
import re
import os
from dotenv import load_dotenv
from pydub import AudioSegment  # 오디오 길이 측정을 위해 필요 (pip install pydub)

# 환경변수(.env) 로드 및 OpenAI API 키 설정
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

async def translate_lyrics(lyrics: List[str]) -> List[str]:
    """가사를 영어로 의역"""
    try:
        # 영어로만 이루어진 가사는 그대로 반환
        if all(is_english(lyric) for lyric in lyrics):
            return lyrics

        system_prompt = "You are a K-pop lyrics translator. Translate Korean lyrics naturally while keeping the emotional context."
        user_prompt = f"Translate these lyrics maintaining the original feeling:\n{lyrics}"

        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        translations = response.choices[0].message.content.strip().split('\n')
        return [clean_translation(line.strip()) for line in translations if line.strip()]
        
    except Exception as e:
        print(f"[DEBUG] 번역 오류: {str(e)}")
        return lyrics  # 오류 시 원본 반환

def is_english(text: str) -> bool:
    """텍스트가 영어로만 이루어져 있는지 확인"""
    return all(char.isascii() or char.isspace() or char in ',.!?-"\'()' for char in text)

def clean_translation(text: str) -> str:
    """번역된 텍스트 정리"""
    # 따옴표, 메타 텍스트, 특수문자 정리
    text = text.strip()
    # 번역 메타 텍스트 제거
    text = re.sub(r'translates to|in English:', '', text)
    # 불필요한 따옴표와 마침표 제거
    text = re.sub(r'^["\']+|["\']+$|\\"|\.+$', '', text)
    # 한글이 그대로 있는 경우 처리
    if re.search(r'[가-힣]', text):
        return "Translation error"
    return text.strip()

def convert_timestamp(timestamp: str) -> float:
    """LRC 타임스탬프를 초 단위로 변환"""
    try:
        minutes, seconds = timestamp.split(':')
        return float(minutes) * 60 + float(seconds)
    except:
        return 0

def format_time(seconds: float) -> str:
    """초 단위 시간을 LRC 타임스탬프 형식으로 변환"""
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"{minutes:02d}:{remaining_seconds:05.2f}"

def seconds_to_srt_timestamp(seconds):
    """
    초 단위의 시간을 SRT 형식의 "HH:MM:SS,mmm" 문자열로 변환합니다.
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    sec = int(seconds % 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{sec:02d},{milliseconds:03d}"

async def parse_lrc_and_translate(lrc_filepath: str, json_filepath: str) -> str:
    try:
        # LRC 파일 존재 확인
        if not os.path.exists(lrc_filepath):
            raise FileNotFoundError(f"LRC 파일을 찾을 수 없습니다: {lrc_filepath}")

        with open(lrc_filepath, 'r', encoding='utf-8') as f:
            lrc_content = f.read()
            
        # 첫 가사 시간 찾기
        first_lyric_time = None
        for line in lrc_content.split('\n'):
            if line.startswith('[') and ']' in line:
                first_lyric_time = line[1:line.index(']')]
                if first_lyric_time:
                    break
        
        # 환경 변수에서 아티스트와 제목 가져오기
        artist = os.getenv('CURRENT_ARTIST', '아티스트')
        title = os.getenv('CURRENT_TITLE', '제목')
        
        # 아티스트-제목 형식의 가사 추가
        if first_lyric_time:
            intro_lyric = f"[{first_lyric_time}]{artist} - {title}\n"
            modified_lrc = intro_lyric + lrc_content
        else:
            modified_lrc = lrc_content
        
        # 가사 데이터 추출 및 번역
        lyrics_data = []
        
        for line in modified_lrc.split('\n'):
            if line.startswith('[') and ']' in line:
                try:
                    time_str = line[1:line.index(']')]
                    text = line[line.index(']')+1:].strip()
                    
                    if text:
                        seconds = convert_timestamp(time_str)
                        translated = await translate_lyrics([text])
                        translated_text = translated[0] if translated else "Translation failed"
                        
                        lyrics_data.append({
                            'start_time': seconds,
                            'original': text,
                            'english': translated_text
                        })
                except Exception as e:
                    print(f"라인 처리 중 오류: {e}")
                    continue

        # 시간순 정렬
        lyrics_data.sort(key=lambda x: x['start_time'])

        # JSON 파일로 저장
        os.makedirs(os.path.dirname(json_filepath), exist_ok=True)
        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(lyrics_data, f, ensure_ascii=False, indent=2)

        print(f"[DEBUG] JSON 파일 생성 완료: {json_filepath}")
        return json_filepath  # json_filepath 반환

    except Exception as e:
        print(f"[ERROR] LRC 파싱/번역 오류: {str(e)}")
        traceback.print_exc()
        raise

def save_lyrics_json(lyrics_data: List[Dict], output_path: str):
    """가사 데이터를 JSON 형식으로 저장"""
    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(lyrics_data, f, ensure_ascii=False, indent=2)

async def generate_srt_from_lrc(lrc_filepath, srt_filepath, audio_filepath=None, default_duration=3.0):
    """
    LRC 파일을 SRT 형식으로 변환하고 번역하는 비동기 함수
    """
    # 오디오 파일 길이 측정 (옵션)
    total_duration = None
    if audio_filepath and os.path.exists(audio_filepath):
        try:
            audio = AudioSegment.from_file(audio_filepath)
            total_duration = len(audio) / 1000.0  # 초 단위
        except Exception as e:
            print("오디오 길이 측정 실패:", e)
    
    # LRC 파일 읽기
    with open(lrc_filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    # LRC 라인 파싱
    subtitles = []
    time_pattern = re.compile(r"\[(\d{2}:\d{2}\.\d{2})\]\s*(.*)")
    for line in lines:
        line = line.strip()
        if not line:
            continue
        match = time_pattern.match(line)
        if match:
            timestamp = match.group(1)
            lyric = match.group(2)
            subtitles.append((timestamp, lyric))
    
    srt_entries = []
    for i, (timestamp, lyric) in enumerate(subtitles):
        start_time = convert_timestamp(f"[{timestamp}]")
        # 종료시간 계산
        if i < len(subtitles) - 1:
            next_timestamp = subtitles[i+1][0]
            end_time = convert_timestamp(f"[{next_timestamp}]")
        else:
            if total_duration is not None:
                end_time = seconds_to_srt_timestamp(total_duration)
            else:
                parts = start_time.split(":")
                sec_parts = parts[2].split(",")
                total_sec = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(sec_parts[0]) + int(sec_parts[1]) / 1000.0
                end_seconds = total_sec + default_duration
                end_time = seconds_to_srt_timestamp(end_seconds)
        
        # 영어 번역 수행 (비동기)
        translation = await translate_lyrics([lyric])
        translated_text = translation[0] if translation else "Translation failed"
        
        srt_entries.append({
            "index": i + 1,
            "start": start_time,
            "end": end_time,
            "original": lyric,
            "translated": translated_text
        })
    
    # SRT 파일 작성
    with open(srt_filepath, "w", encoding="utf-8") as f:
        for entry in srt_entries:
            f.write(f"{entry['index']}\n")
            f.write(f"{entry['start']} --> {entry['end']}\n")
            f.write(f"{entry['original']}\n")
            f.write(f"{entry['translated']}\n\n")
    
    print(f"SRT 파일 생성 완료: {srt_filepath}")
    return srt_filepath
