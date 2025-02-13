import os
import json
import traceback
import asyncio
from dataclasses import dataclass
from typing import Callable, Optional

from youtube_handler import youtube_search, download_youtube_audio
from genie_handler import get_genie_lyrics, search_genie_songs, get_song_details
from openai_handler import parse_lrc_and_translate
from video_maker import make_lyric_video
from album_art_finder import download_album_art

@dataclass
class ProcessConfig:
    title: str
    artist: str
    album_art_url: str
    youtube_url: str
    target_dir: str = "temp"
    output_dir: str = "output"

class ProcessManager:
    def __init__(self, update_progress: Callable[[str, int], None]):
        self.update_progress = update_progress

    async def process_async(self, config: ProcessConfig):
        try:
            print("[DEBUG] 작업 프로세스 시작")
            
            # 디렉토리 생성
            for dir_path in ["temp", "output", "result"]:
                os.makedirs(dir_path, exist_ok=True)
                print(f"[DEBUG] 디렉토리 확인: {dir_path}")
                
            # 파일명 생성
            filename = self._sanitize_filename(f"{config.artist} - {config.title}")
            audio_path = f"temp/{filename}.mp3"
            image_path = f"temp/{filename}.jpg"
            json_path = f"temp/{filename}_lyrics.json"
            output_path = f"output/{filename}.mp4"
            
            print("[DEBUG] 파일 경로 설정 완료:")
            print(f"- 오디오: {audio_path}")
            print(f"- 이미지: {image_path}")
            print(f"- 가사: {json_path}")
            print(f"- 출력: {output_path}")
            
            # YouTube 다운로드
            self.update_progress("YouTube 오디오 다운로드 중...", 20)
            print(f"[DEBUG] YouTube 다운로드 시작: {config.youtube_url}")
            if not download_youtube_audio(config.youtube_url, filename):
                raise Exception("YouTube 오디오 다운로드 실패")
            print(f"[DEBUG] YouTube 다운로드 완료")
            
            # 앨범 아트 다운로드
            self.update_progress("앨범 아트 다운로드 중...", 40)
            print(f"[DEBUG] 앨범 아트 다운로드 시작: {config.album_art_url}")
            if not download_album_art(config.album_art_url, image_path):
                raise Exception("앨범 아트 다운로드 실패")
            print("[DEBUG] 앨범 아트 다운로드 완료")
            
            # LRC 파일 찾기
            self.update_progress("가사 파일 처리 중...", 60)
            lrc_files = [f for f in os.listdir("result") if f.endswith(".lrc")]
            if not lrc_files:
                raise Exception("가사 파일을 찾을 수 없습니다")
            lrc_path = os.path.join("result", lrc_files[0])
            print(f"[DEBUG] LRC 파일 발견: {lrc_path}")
            
            # 가사 번역
            try:
                self.update_progress("가사 번역 중...", 80)
                print("[DEBUG] 가사 번역 시작")
                os.environ['CURRENT_ARTIST'] = config.artist
                os.environ['CURRENT_TITLE'] = config.title
                lyrics_json_path = await parse_lrc_and_translate(lrc_path, json_path)
                print(f"[DEBUG] 가사 번역 완료: {lyrics_json_path}")
            finally:
                os.environ.pop('CURRENT_ARTIST', None)
                os.environ.pop('CURRENT_TITLE', None)
            
            # 비디오 생성
            try:
                self.update_progress("리릭 비디오 생성 중...", 90)
                print("[DEBUG] 비디오 생성 시작")
                
                # 필요한 파일들 확인
                for file_path in [audio_path, image_path, lyrics_json_path]:
                    if not os.path.exists(file_path):
                        raise Exception(f"필요한 파일이 없습니다: {file_path}")
                
                make_lyric_video(
                    audio_path=audio_path,
                    album_art_path=image_path,
                    lyrics_json_path=lyrics_json_path,
                    output_path=output_path
                )
                print(f"[DEBUG] 비디오 생성 완료: {output_path}")
                
                return output_path
                
            except Exception as e:
                print(f"[ERROR] 비디오 생성 중 오류 발생: {str(e)}")
                traceback.print_exc()
                raise
                
        except Exception as e:
            print(f"[ERROR] 처리 중 오류 발생: {str(e)}")
            traceback.print_exc()
            raise

    def process(self, config: ProcessConfig):
        """동기 래퍼 메서드"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.process_async(config))

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        import re
        return re.sub(r'[\\/*?:"<>|]', "_", filename)

    def validate_config(self, config: ProcessConfig) -> Optional[str]:
        if not all([config.title, config.artist, config.album_art_url, config.youtube_url]):
            return "제목, 아티스트, 앨범 아트 URL, YouTube URL을 모두 입력해주세요."
        return None
