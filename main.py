from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                           QRadioButton, QFrame, QScrollArea, QMessageBox, QButtonGroup, QTextEdit)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage, QPainter
import sys
import requests
from io import BytesIO

from youtube_handler import youtube_search, download_youtube_audio
from genie_handler import search_genie_songs, get_song_details, parse_genie_extra_info, get_genie_lyrics
from openai_handler import parse_lrc_and_translate
from video_maker import make_lyric_video
from ui_components import create_youtube_result_item, ProgressWindow
from album_art_finder import search_album_art_bugs, download_album_art
from process_manager import ProcessManager, ProcessConfig # 이 줄을 추가

import os
import re
import urllib.parse
import webbrowser
import threading
import traceback

from ui_components import (
    load_image_from_url, create_youtube_result_item, 
    create_album_art_preview, update_album_art_preview,
    create_genie_result_item
)

import asyncio

# 헬퍼 함수: 파일명에 사용할 수 없는 문자를 "_"로 치환
def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "_", filename)

# 전역 변수: YouTube 검색 결과 리스트
youtube_results = []

class WorkerThread(QThread):
    progress = pyqtSignal(str, int)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.process_manager = ProcessManager(self.update_progress)

    def run(self):
        try:
            config = ProcessConfig(
                title=self.main_window.title_input.text().strip(),
                artist=self.main_window.artist_input.text().strip(),
                album_art_url=self.main_window.album_cover_input.text().strip(),
                youtube_url=self.main_window.selected_youtube.get('link', '')  # 'url' -> 'link' 수정
            )
            
            # ProcessManager를 통한 처리
            output_path = self.process_manager.process(config)
            
            if output_path and os.path.exists(output_path):
                print(f"[DEBUG] 처리 완료. 출력 파일: {output_path}")
                self.finished.emit()
            else:
                raise Exception("출력 파일이 생성되지 않았습니다.")
                
        except Exception as e:
            print(f"[ERROR] WorkerThread 오류: {str(e)}")
            traceback.print_exc()
            self.error.emit(str(e))

    async def process_async(self, config):
        try:
            print("[DEBUG] 비동기 처리 시작")
            
            # 디렉토리 확인
            print("[DEBUG] 디렉토리 확인 중...")
            if not os.path.exists("result"):
                print("[DEBUG] result 디렉토리가 없습니다. 생성합니다.")
                os.makedirs("result")
            
            # LRC 파일 검색
            print("[DEBUG] LRC 파일 검색 중...")
            lrc_files = [f for f in os.listdir("result") if f.endswith(".lrc")]
            print(f"[DEBUG] 발견된 LRC 파일: {lrc_files}")
            
            if not lrc_files:
                print("[ERROR] LRC 파일을 찾을 수 없습니다.")
                raise Exception("가사 파일을 찾을 수 없습니다.")
                
            # LRC 파일 경로 설정
            lrc_path = os.path.join("result", lrc_files[0])
            print(f"[DEBUG] 선택된 LRC 파일 경로: {lrc_path}")
            
            # JSON 파일 경로 설정
            filename = sanitize_filename(f"{config.artist} - {config.title}")
            json_path = f"temp/{filename}_lyrics.json"
            print(f"[DEBUG] JSON 파일 저장 경로: {json_path}")
            
            # 환경 변수 설정
            print("[DEBUG] 환경 변수 설정...")
            os.environ['CURRENT_ARTIST'] = config.artist
            os.environ['CURRENT_TITLE'] = config.title
            print(f"[DEBUG] 아티스트: {config.artist}")
            print(f"[DEBUG] 제목: {config.title}")
            
            try:
                # 가사 번역 시작
                print("[DEBUG] 가사 번역 프로세스 시작...")
                lyrics_json = await parse_lrc_and_translate(lrc_path, json_path)
                print(f"[DEBUG] 가사 번역 완료. JSON 파일 생성됨: {lyrics_json}")
                
            except Exception as e:
                print(f"[ERROR] 가사 번역 중 오류 발생: {str(e)}")
                traceback.print_exc()
                raise
                
            finally:
                # 환경 변수 정리
                print("[DEBUG] 환경 변수 정리...")
                os.environ.pop('CURRENT_ARTIST', None)
                os.environ.pop('CURRENT_TITLE', None)
            
            return True
                
        except Exception as e:
            print(f"[ERROR] process_async 처리 중 오류: {str(e)}")
            traceback.print_exc()
            return False

    def update_progress(self, message: str, percent: int):
        self.progress.emit(message, percent)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("노래 검색 및 리릭 비디오 생성")
        self.setMinimumSize(1200, 800)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # 검색 영역
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("검색어:"))
        self.search_input = QLineEdit()
        search_button = QPushButton("검색")
        search_button.clicked.connect(self.submit_search)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(search_button)
        main_layout.addLayout(search_layout)
        
        # 2열 컨테이너
        columns_layout = QHBoxLayout()
        
        # 왼쪽 열: 지니뮤직 검색 결과 + 입력 필드
        left_column = QVBoxLayout()
        
        # 지니뮤직 검색 결과
        genie_group = QFrame()
        genie_group.setFrameStyle(QFrame.Shape.Box)
        genie_layout = QVBoxLayout(genie_group)
        genie_layout.addWidget(QLabel("지니뮤직 검색 결과"))
        
        self.genie_results_widget = QScrollArea()
        self.genie_results_widget.setWidgetResizable(True)
        genie_content = QWidget()
        self.genie_results_layout = QVBoxLayout(genie_content)
        self.genie_results_widget.setWidget(genie_content)
        genie_layout.addWidget(self.genie_results_widget)
        
        # 검색 결과 적용 버튼
        apply_button = QPushButton("검색 결과 적용")
        apply_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 12px;
                font-weight: bold;
                border-radius: 3px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        apply_button.clicked.connect(self.apply_selected_genie)
        genie_layout.addWidget(apply_button)
        
        # 입력 필드 추가
        input_group = self.create_input_section()
        genie_layout.addWidget(input_group)
        
        left_column.addWidget(genie_group)
        
        # 오른쪽 열: YouTube 결과
        right_column = QVBoxLayout()
        youtube_group = QFrame()
        youtube_group.setFrameStyle(QFrame.Shape.Box)
        youtube_layout = QVBoxLayout(youtube_group)
        youtube_layout.addWidget(QLabel("YouTube 검색 결과"))
        
        self.youtube_results_widget = QScrollArea()
        self.youtube_results_widget.setWidgetResizable(True)
        youtube_content = QWidget()
        self.youtube_results_layout = QVBoxLayout(youtube_content)
        self.youtube_results_widget.setWidget(youtube_content)
        youtube_layout.addWidget(self.youtube_results_widget)
        right_column.addWidget(youtube_group)
        
        # 2개의 열을 메인 레이아웃에 추가
        columns_layout.addLayout(left_column, stretch=1)
        columns_layout.addLayout(right_column, stretch=1)
        
        columns_container = QWidget()
        columns_container.setLayout(columns_layout)
        main_layout.addWidget(columns_container)
        
        # 처리 버튼
        process_button = QPushButton("선택 완료 후 처리")
        process_button.setFixedHeight(40)
        process_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        process_button.clicked.connect(self.process_selection)
        main_layout.addWidget(process_button)
        
        self.genie_results = []
        self.youtube_results = []  # youtube_results를 클래스 변수로 변경
        self.selected_youtube = None  # selected_youtube 초기화 추가
        self.worker = None
        
        # 라디오 버튼 그룹
        self.genie_button_group = QButtonGroup(self)
        self.youtube_button_group = QButtonGroup(self)

    def update_album_art(self, url):
        """앨범 아트 업데이트"""
        try:
            pixmap = load_image_from_url(url)  # ui_components의 함수 사용
            if (pixmap):
                scaled_pixmap = pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio)
                self.album_art_preview.setPixmap(scaled_pixmap)  # album_art_preview 사용
        except Exception as e:
            print(f"앨범 아트 업데이트 실패: {e}")

    def submit_search(self):
        """검색 실행"""
        query = self.search_input.text().strip()
        print(f"\n[DEBUG] 검색 시작 - 검색어: {query}")
        
        if not query:
            QMessageBox.warning(self, "경고", "검색어를 입력하세요.")
            return

        # 지니뮤직 검색
        try:
            print("[DEBUG] 지니뮤직 검색 시작")
            self.genie_results = search_genie_songs(query)  # 결과 저장
            print(f"[DEBUG] 검색 결과 받음: {len(self.genie_results)}개")
            
            # 기존 결과 위젯 초기화
            print("[DEBUG] UI 초기화 시작")
            for i in reversed(range(self.genie_results_layout.count())): 
                self.genie_results_layout.itemAt(i).widget().deleteLater()
                
            # 새 검색 결과 추가
            print("[DEBUG] 검색 결과 UI 생성 시작")
            for idx, (title, song_id, extra_info, album_art_url) in enumerate(self.genie_results):
                try:
                    print(f"\n[DEBUG] {idx+1}번째 결과 처리 중:")
                    print(f"  - 제목: {title}")
                    print(f"  - ID: {song_id}")
                    print(f"  - 추가정보: {extra_info}")
                    print(f"  - 앨범아트 URL: {album_art_url}")
                    
                    artist, album = parse_genie_extra_info(extra_info)
                    
                    item = create_genie_result_item(
                        self.genie_results_widget,
                        idx,
                        title,
                        artist,
                        album,
                        self,
                        album_art_url  # 앨범 아트 URL 추가
                    )
                    self.genie_results_layout.addWidget(item)
                    print(f"[DEBUG] {idx+1}번째 결과 UI 생성 완료")
                    
                except Exception as e:
                    print(f"[DEBUG] 결과 처리 실패: {e}")
                    traceback.print_exc()

        except Exception as e:
            print(f"[DEBUG] 검색 실패: {e}")
            traceback.print_exc()

    # YouTube 검색 부분
        try:
            self.youtube_results = youtube_search(query)
            
            # 기존 결과 위젯 초기화
            for i in reversed(range(self.youtube_results_layout.count())): 
                self.youtube_results_layout.itemAt(i).widget().deleteLater()
            
            # 새 검색 결과 추가
            for idx, result in enumerate(self.youtube_results):
                item = create_youtube_result_item(
                    self.youtube_results_widget,
                    result,  # 이미 형식이 맞춰진 결과를 그대로 전달
                    idx,
                    self
                )
                self.youtube_results_layout.addWidget(item)
        except Exception as e:
            print(f"YouTube 검색 실패: {e}")
            traceback.print_exc()

    def on_genie_selection(self, idx):
        """지니뮤직 항목 선택 시 처리"""
        try:
            title, song_id, extra_info, album_art_url = self.genie_results[idx]
            artist, album = parse_genie_extra_info(extra_info)
            
            # 입력 필드 업데이트
            self.title_input.setText(title)
            self.artist_input.setText(artist)
            self.album_cover_input.setText(album_art_url)
            self.update_album_art(album_art_url)
            
        except Exception as e:
            print(f"지니뮤직 선택 처리 실패: {e}")

    def on_album_url_changed(self):
        """앨범 아트 URL 변경 시 처리"""
        url = self.album_cover_input.text().strip()
        if url:
            self.update_album_art(url)

    def on_youtube_selection(self, idx):
        """YouTube 항목 선택 시 처리"""
        try:
            if idx < len(self.youtube_results):
                selected = self.youtube_results[idx]
                self.selected_youtube = {
                    'title': selected.get('title', ''),
                    'link': selected.get('link', ''),
                    'thumbnail': selected.get('thumbnail', '')
                }
                print(f"[DEBUG] YouTube 영상 선택됨: {selected.get('title', '')}")
                print(f"[DEBUG] 선택된 URL: {selected.get('link', '')}")
        except Exception as e:
            print(f"[DEBUG] YouTube 선택 처리 실패: {str(e)}")
            traceback.print_exc()

    def process_selection(self):
        """선택 완료 후 처리"""
        if not self.worker:
            # 현재 창 숨기기
            self.hide()
            
            # 진행 상황 창 생성 및 표시
            self.progress_window = ProgressWindow()
            self.progress_window.show()
            
            # 작업 스레드 시작
            self.worker = WorkerThread(self)  # self를 전달하여 메인 윈도우 참조
            self.worker.progress.connect(self.progress_window.update_progress)
            self.worker.finished.connect(self.on_process_complete)
            self.worker.error.connect(self.on_error)
            self.worker.start()

    def on_process_complete(self):
        """작업 완료 처리"""
        self.progress_window.close()
        QMessageBox.information(self, "완료", "작업이 완료되었습니다.")
        self.worker = None
        self.show()  # 메인 창 다시 표시

    def on_error(self, error_message):
        """에러 처리"""
        self.progress_window.close()
        QMessageBox.critical(self, "오류", f"작업 중 오류가 발생했습니다:\n{error_message}")
        self.worker = None
        self.show()  # 메인 창 다시 표시

    def update_progress(self, message, value):
        self.progress_label.setText(f"진행 상황: {message}")

    def apply_selected_genie(self):
        """지니뮤직 선택 결과 적용"""
        try:
            selected_button = self.genie_button_group.checkedButton()
            if not selected_button:
                return
                
            idx = self.genie_button_group.id(selected_button)
            title, song_id, extra_info, album_art_url = self.genie_results[idx]
            artist, album = parse_genie_extra_info(extra_info)
            
            # 기본 정보 업데이트
            self.title_input.setText(title)
            self.artist_input.setText(artist)
            self.album_cover_input.setText(album_art_url)
            
            # 가사 자동으로 가져오기만 실행 (화면에 표시하지 않음)
            try:
                _ = get_genie_lyrics(song_id)
                print(f"[DEBUG] 가사 파일 생성 완료: {title}")
            except Exception as e:
                print(f"[DEBUG] 가사 가져오기 실패: {e}")
                
        except Exception as e:
            print(f"[DEBUG] 선택 결과 적용 실패: {e}")

    def on_album_art_selected(self, idx):
        """앨범 아트 선택 시 처리"""
        try:
            _, _, _, album_art_url = self.genie_results[idx]
            self.album_cover_input.setText(album_art_url)
            self.update_album_art(album_art_url)
        except Exception as e:
            print(f"앨범 아트 선택 처리 실패: {e}")

    def create_album_art_section(self):
        """앨범 아트 섹션 생성"""
        album_art_group = QFrame()
        album_art_group.setFrameStyle(QFrame.Shape.Box)
        album_art_layout = QVBoxLayout(album_art_group)
        
        # 제목
        album_art_layout.addWidget(QLabel("앨범 아트 선택"))
        
        # 앨범 아트 라디오 버튼 그룹
        self.album_art_button_group = QButtonGroup(self)
        
        # 앨범 아트 스크롤 영역
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFixedHeight(250)  # 스크롤 영역 높이 제한
        
        scroll_content = QWidget()
        self.album_art_layout = QVBoxLayout(scroll_content)
        scroll_area.setWidget(scroll_content)
        album_art_layout.addWidget(scroll_area)
        
        # URL 직접 입력
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("URL:"))
        self.album_cover_input = QLineEdit()
        self.album_cover_input.textChanged.connect(self.on_album_url_changed)
        url_layout.addWidget(self.album_cover_input)
        album_art_layout.addLayout(url_layout)
        
        # 미리보기
        self.album_art_preview = QLabel()
        self.album_art_preview.setFixedSize(200, 200)
        self.album_art_preview.setStyleSheet("""
            background-color: lightgrey;
            border: 1px solid #ccc;
        """)
        album_art_layout.addWidget(self.album_art_preview)
        
        return album_art_group

    def create_album_art_item(self, url: str, idx: int):
        """앨범 아트 아이템 위젯 생성"""
        item = QWidget()
        layout = QHBoxLayout(item)
        
        radio = QRadioButton()
        self.album_art_button_group.addButton(radio, idx)
        layout.addWidget(radio)
        
        preview = QLabel()
        preview.setFixedSize(100, 100)
        pixmap = load_image_from_url(url)
        if (pixmap):
            preview.setPixmap(pixmap.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio))
        layout.addWidget(preview)
        
        radio.clicked.connect(lambda: self.on_album_art_selected(url))
        return item

    def on_album_art_selected(self, url: str):
        """앨범 아트 선택 시 처리"""
        self.album_cover_input.setText(url)
        self.update_album_art(url)

    def create_input_section(self):
        """입력 필드 섹션 생성"""
        input_group = QFrame()
        input_group.setFrameStyle(QFrame.Shape.Box)
        input_layout = QVBoxLayout(input_group)

        # 제목, 아티스트 입력
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("제목:"))
        self.title_input = QLineEdit()
        title_layout.addWidget(self.title_input)
        input_layout.addLayout(title_layout)

        artist_layout = QHBoxLayout()
        artist_layout.addWidget(QLabel("아티스트:"))
        self.artist_input = QLineEdit()
        artist_layout.addWidget(self.artist_input)
        input_layout.addLayout(artist_layout)

        # 앨범 아트 URL
        album_art_layout = QHBoxLayout()
        album_art_layout.addWidget(QLabel("앨범 아트 URL:"))
        self.album_cover_input = QLineEdit()
        self.album_cover_input.textChanged.connect(self.on_album_url_changed)
        album_art_layout.addWidget(self.album_cover_input)
        input_layout.addLayout(album_art_layout)

        return input_group

if __name__ == '__main__':

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
