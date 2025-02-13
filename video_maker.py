import os
from typing import List, Dict
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.io.ImageSequenceClip import ImageSequenceClip
from moviepy.video.VideoClip import ImageClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
import numpy as np
import re
import json
import traceback

def draw_outlined_text(draw, pos, text, font, text_color=(255, 255, 255), outline_color=(0, 0, 0), outline_width=3):
    """테두리가 있는 텍스트 그리기"""
    x, y = pos
    # 테두리 그리기
    for offset_x in range(-outline_width, outline_width + 1):
        for offset_y in range(-outline_width, outline_width + 1):
            draw.text((x + offset_x, y + offset_y), text, font=font, fill=outline_color)
    # 메인 텍스트 그리기
    draw.text((x, y), text, font=font, fill=text_color)

def create_lyric_frame(background_img: Image.Image, lyric: Dict[str, str], font_path: str) -> Image.Image:
    """각 가사 프레임 생성"""
    # 배경 이미지 블러 처리
    frame = background_img.copy()
    frame = frame.filter(ImageFilter.GaussianBlur(radius=15))
    
    # 투명도 레이어 추가
    overlay = Image.new('RGBA', frame.size, (0, 0, 0, 128))
    frame = Image.alpha_composite(frame.convert('RGBA'), overlay)
    
    draw = ImageDraw.Draw(frame)
    
    # 폰트 설정
    korean_font = ImageFont.truetype(font_path, 70)  # 한글 가사용
    english_font = ImageFont.truetype(font_path, 50)  # 영문 가사용
    
    # 한글 가사 위치 계산
    k_text = lyric['original']
    k_bbox = draw.textbbox((0, 0), k_text, font=korean_font)
    k_width = k_bbox[2] - k_bbox[0]
    k_x = (frame.width - k_width) // 2
    k_y = frame.height // 2 - 100
    
    # 영문 가사 위치 계산
    e_text = lyric['english']
    e_bbox = draw.textbbox((0, 0), e_text, font=english_font)
    e_width = e_bbox[2] - e_bbox[0]
    e_x = (frame.width - e_width) // 2
    e_y = frame.height // 2 + 20
    
    # 테두리가 있는 텍스트 그리기
    draw_outlined_text(draw, (k_x, k_y), k_text, korean_font)
    draw_outlined_text(draw, (e_x, e_y), e_text, english_font)
    
    return frame

def parse_srt_file(srt_path: str):
    """SRT 파일 파싱"""
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    segments = content.strip().split('\n\n')
    lyrics_data = []
    
    for segment in segments:
        lines = segment.split('\n')
        if len(lines) >= 3:
            times = lines[1].split(' --> ')
            start_time = times[0].replace(',', '.')
            end_time = times[1].replace(',', '.')
            text = '\n'.join(lines[2:])  # 한글 가사와 영어 가사 모두 포함
            lyrics_data.append({
                'start': start_time,
                'end': end_time,
                'text': text
            })
    
    return lyrics_data

def make_lyric_video(audio_path: str, album_art_path: str, lyrics_json_path: str, output_path: str):
    """리릭 비디오 생성"""
    try:
        print("[DEBUG] 리릭 비디오 생성 시작")
        
        # 오디오 로드
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        
        # 앨범아트 로드 및 크기 조정
        background_img = Image.open(album_art_path)
        background_img = background_img.resize((1920, 1080), Image.Resampling.LANCZOS)
        background_img = background_img.convert('RGBA')
        
        # 가사 JSON 로드
        with open(lyrics_json_path, 'r', encoding='utf-8') as f:
            lyrics_data = json.load(f)
        
        # 클립 생성
        clips = []
        
        # 각 가사에 대한 클립 생성
        for i, lyric in enumerate(lyrics_data):
            frame = create_lyric_frame(background_img.copy(), lyric, "C:/Windows/Fonts/malgunbd.ttf")
            frame_array = np.array(frame)
            
            # 시작 시간과 지속 시간 계산
            start_time = float(lyric['start_time'])
            if i < len(lyrics_data) - 1:
                end_time = float(lyrics_data[i+1]['start_time'])
            else:
                end_time = duration
                
            # 클립 생성 및 추가
            clip = (ImageClip(frame_array)
                   .with_duration(end_time - start_time)
                   .with_start(start_time))
            clips.append(clip)

        # 배경 클립 생성
        bg_array = np.array(background_img)
        background = ImageClip(bg_array).with_duration(duration)
        
        # 모든 클립 합성
        final = CompositeVideoClip([background] + clips, size=(1920, 1080))
        final = final.with_audio(audio)
        
        # 비디오 파일 생성
        final.write_videofile(
            output_path,
            fps=24,
            codec='libx264',
            audio_codec='aac',
            threads=4,
            preset='ultrafast'
        )
        
        # 리소스 정리
        audio.close()
        final.close()
        
        print(f"[DEBUG] 리릭 비디오 생성 완료: {output_path}")
        
    except Exception as e:
        print(f"[ERROR] 비디오 생성 실패: {str(e)}")
        traceback.print_exc()
        raise e

def convert_timestamp_to_seconds(timestamp: str) -> float:
    """SRT 타임스탬프를 초 단위로 변환"""
    hours, minutes, seconds = timestamp.replace(',', '.').split(':')
    return float(hours) * 3600 + float(minutes) * 60 + float(seconds)

def convert_to_seconds(time_str):
    """시간 형식 (HH:MM:SS,ms)을 초 단위로 변환하는 함수."""
    try:
        parts = re.split('[:,]', time_str)
        if len(parts) != 4:
            raise ValueError(f"잘못된 시간 형식: {time_str}")
        h, m, s, ms = parts
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
    except Exception as e:
        print(f"convert_to_seconds 오류: {e}")
        return 0  # 오류 발생 시 0초로 반환

def convert_milliseconds_to_seconds(milliseconds: float) -> float:
    """밀리초를 초 단위로 변환"""
    return milliseconds / 1000

def parse_lyrics_json(json_path: str) -> List[dict]:
    """JSON 가사 파일 파싱"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)