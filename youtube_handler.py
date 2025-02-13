# youtube_handler.py

from youtubesearchpython import VideosSearch
import yt_dlp
import os

def youtube_search(query):
    """YouTube에서 최대 3개의 검색 결과를 반환"""
    try:
        videosSearch = VideosSearch(query + " audio", limit=3)
        results = videosSearch.result()
        # 결과 형식 통일
        formatted_results = []
        for result in results.get("result", []):
            formatted_results.append({
                'title': result.get('title', ''),
                'link': result.get('link', ''),
                'thumbnail': result.get('thumbnails', [{'url': ''}])[0]['url'],
                'duration': result.get('duration', 'N/A')
            })
        return formatted_results
    except Exception as e:
        print(f"YouTube 검색 실패: {e}")
        return []

def download_youtube_audio(url: str, output_filename: str) -> bool:
    """YouTube 동영상의 오디오를 MP3로 바로 다운로드"""
    try:
        output_filename = os.path.splitext(output_filename)[0]
        ydl_opts = {
            'format': 'bestaudio/best',
            'extract_audio': True,
            'audio_format': 'mp3',
            'audio_quality': '192K',
            'outtmpl': f'temp/{output_filename}',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True,
            'noprogress': True,
            'noplaylist': True,
            'overwrites': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"[DEBUG] MP3 다운로드 시작: {output_filename}")
            ydl.download([url])
            
            output_path = f'temp/{output_filename}.mp3'
            if os.path.exists(output_path):
                print(f"[DEBUG] MP3 다운로드 완료: {output_path}")
                return True
                
        return False

    except Exception as e:
        print(f"[ERROR] MP3 다운로드 실패: {str(e)}")
        return False
