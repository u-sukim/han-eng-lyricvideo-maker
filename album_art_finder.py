import musicbrainzngs
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
from typing import Optional
import traceback

# MusicBrainz API 설정
musicbrainzngs.set_useragent(
    "LyricVideoMaker",
    "1.0",
    "https://github.com/yourusername/LyricVideoMaker"
)

def search_album_art(artist: str, title: str) -> Optional[str]:
    """
    아티스트와 곡 제목으로 앨범 아트 URL 검색
    """
    try:
        # 곡 검색
        result = musicbrainzngs.search_recordings(
            artist=artist,
            recording=title,
            limit=1
        )
        
        if not result['recording-list']:
            return None
            
        # 첫 번째 검색 결과의 릴리즈 그룹 ID 가져오기
        recording = result['recording-list'][0]
        if 'release-list' not in recording:
            return None
            
        release_id = recording['release-list'][0]['id']
        
        # 릴리즈 정보에서 커버 아트 URL 가져오기
        release_info = musicbrainzngs.get_image_list(release_id)
        
        if release_info['images']:
            # 가장 큰 이미지 선택
            images = [img for img in release_info['images'] if 'front' in img['types']]
            if images:
                return max(images, key=lambda x: x.get('thumbnails', {}).get('large', ''))['thumbnails']['large']
                
    except Exception as e:
        print(f"앨범 아트 검색 실패: {e}")
        
    return None

def search_album_art_bugs(artist: str, title: str) -> Optional[str]:
    """
    Bugs에서 앨범 아트 URL 검색
    """
    try:
        # 검색 쿼리 생성
        query = quote(f"{artist} {title}")
        url = f"https://music.bugs.co.kr/search/track?q={query}"
        
        # 검색 페이지 요청
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # HTML 파싱
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 첫 번째 검색 결과의 앨범 아트 찾기
        album_art = soup.select_one('table.trackList > tbody > tr:first-child figure.thumbnail img')
        if album_art and 'src' in album_art.attrs:
            # 고화질 이미지 URL로 변환
            image_url = album_art['src'].replace('50x50', '1000x1000')
            if image_url.startswith('//'):
                image_url = 'https:' + image_url
            return image_url
            
    except Exception as e:
        print(f"Bugs 앨범 아트 검색 실패: {e}")
        traceback.print_exc()
        
    return None

def download_album_art(url: str, filepath: str) -> bool:
    """
    URL에서 앨범 아트 다운로드
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            f.write(response.content)
        return True
        
    except Exception as e:
        print(f"앨범 아트 다운로드 실패: {e}")
        return False