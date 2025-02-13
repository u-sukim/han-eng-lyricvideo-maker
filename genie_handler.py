from genieapi import GenieAPI
from typing import List, Tuple, Optional
import requests
import traceback
from bs4 import BeautifulSoup

def search_genie_songs(query: str, limit: int = 4) -> List[Tuple[str, str, str, str]]:
    """지니뮤직에서 노래 검색"""
    try:
        print(f"[DEBUG] 지니뮤직 검색 시작: 검색어 '{query}'")
        genie = GenieAPI()
        songs = genie.search_song(query, limit=limit)  # limit 파라미터 추가
        print(f"[DEBUG] GenieAPI 검색 결과: {len(songs)}개")
        
        results = []
        for idx, (title, song_id, extra_info) in enumerate(songs):
            try:
                print(f"\n[DEBUG] {idx+1}번째 곡 처리 중:")
                print(f"  - 제목: {title}")
                print(f"  - ID: {song_id}")
                print(f"  - 추가정보: {extra_info}")
                
                # 앨범 아트 URL 가져오기
                album_art_url = get_album_art_url(song_id)
                print(f"  - 앨범아트 URL: {album_art_url}")
                
                results.append((title, song_id, extra_info, album_art_url))
                print(f"[DEBUG] {idx+1}번째 곡 처리 완료")
                
            except Exception as e:
                print(f"[DEBUG] 곡 정보 처리 실패: {e}")
                traceback.print_exc()
                continue
        
        return results

    except Exception as e:
        print(f"[DEBUG] 지니뮤직 검색 실패: {e}")
        traceback.print_exc()
        return []

def get_genie_lyrics(song_id: str) -> Optional[str]:
    """지니뮤직에서 가사 가져오기"""
    try:
        genie = GenieAPI()
        lyrics = genie.get_lyrics(song_id)
        print(f"[DEBUG] 가사 가져오기 성공: {song_id}")
        return lyrics
    except Exception as e:
        print(f"[DEBUG] 가사 가져오기 실패: {e}")
        return None

def parse_genie_extra_info(extra_info: str) -> Tuple[str, str]:
    """추가 정보에서 아티스트와 앨범 분리"""
    parts = extra_info.split(' - ', 1)
    artist = parts[0].strip()
    album = parts[1].strip() if len(parts) > 1 else ""
    return artist, album

def get_album_art_url(song_id: str) -> Optional[str]:
    """지니뮤직에서 앨범 아트 URL 가져오기"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        # 곡 정보 페이지에서 앨범 정보 가져오기
        song_url = f"https://www.genie.co.kr/detail/songInfo?xgnm={song_id}"
        print(f"[DEBUG] 곡 정보 URL: {song_url}")
        response = requests.get(song_url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # HTML 구조에 맞는 선택자로 변경
        album_img = soup.select_one('div.photo-zone span.cover > img')
        if album_img and 'src' in album_img.attrs:
            img_url = album_img['src']
            if img_url.startswith('//'):
                img_url = 'https:' + img_url
            
            # 고화질 이미지 URL로 변환
            img_url = img_url.replace('/dims/resize/Q_80,0', '')
            print(f"[DEBUG] 앨범 아트 URL 찾음: {img_url}")
            return img_url
            
        print("[DEBUG] 앨범 아트를 찾을 수 없습니다.")
        print("[DEBUG] HTML 구조:")
        print(soup.select_one('div.photo-zone'))
            
    except Exception as e:
        print(f"[DEBUG] 앨범 아트 URL 가져오기 실패: {e}")
        traceback.print_exc()
        
    return None

def get_album_arts_url(song_id: str) -> List[str]:
    """지니뮤직에서 여러 앨범 아트 URL 가져오기"""
    urls = []
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        # 곡 정보 페이지
        url = f"https://www.genie.co.kr/detail/songInfo?xgnm={song_id}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        album_img = soup.select_one('a.cover > img')
        if album_img and 'src' in album_img.attrs:
            img_url = album_img['src']
            if img_url.startswith('//'):
                img_url = 'https:' + img_url
            urls.append(img_url.replace('/cover/size80/', '/cover/ori/'))
            
        # 아티스트 페이지에서 추가 앨범 아트 검색
        artist_link = soup.select_one('a.artist-info')
        if artist_link and 'href' in artist_link.attrs:
            artist_url = f"https://www.genie.co.kr{artist_link['href']}"
            artist_response = requests.get(artist_url, headers=headers)
            artist_soup = BeautifulSoup(artist_response.text, 'html.parser')
            album_imgs = artist_soup.select('div.album-list img')[:2]  # 추가로 2개만
            
            for img in album_imgs:
                if 'src' in img.attrs:
                    img_url = img['src']
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                    urls.append(img_url.replace('/cover/size80/', '/cover/ori/'))
            
    except Exception as e:
        print(f"앨범 아트 URL 가져오기 실패: {e}")
        
    return urls

def get_song_details(song_id: str) -> Optional[Tuple[str, str]]:
    """지니뮤직에서 앨범 아트 URL과 앨범 ID 가져오기"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        url = f"https://www.genie.co.kr/detail/songInfo?xgnm={song_id}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        album_img = soup.select_one('a.cover > img')
        
        if album_img and 'src' in album_img.attrs:
            img_url = album_img['src']
            if img_url.startswith('//'):
                img_url = 'https:' + img_url
            album_id = img_url.split('/')[-1].split('.')[0]
            return img_url.replace('/cover/size140/', '/cover/ori/'), album_id
            
    except Exception as e:
        print(f"앨범 정보 가져오기 실패: {e}")
        traceback.print_exc()
        
    return None
