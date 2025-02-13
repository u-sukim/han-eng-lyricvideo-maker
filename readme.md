# Lyric Video Maker

**Lyric Video Maker**는 여러 API와 라이브러리를 활용하여 노래 검색, 가사 번역, 앨범 아트 및 오디오 다운로드, 그리고 최종적으로 리릭 비디오를 생성하는 파이썬 애플리케이션입니다.  
이 프로젝트는 PyQt6 기반의 GUI를 제공하며, 다음과 같은 기능들을 통합합니다.

## 주요 기능

- **노래 검색**  
  - **Genie API**를 통해 노래 정보(제목, 아티스트, 앨범, 가사 등)를 검색합니다.
  - YouTube 검색을 통해 오디오 소스를 선택할 수 있습니다.

- **앨범 아트 검색**  
  - MusicBrainz 및 Bugs 웹 스크래핑을 통해 앨범 아트 이미지를 검색하고 다운로드합니다.

- **가사 번역**  
  - LRC 파일을 파싱한 후, OpenAI API(GPT-3.5)를 이용해 가사를 자연스러운 영어로 번역합니다.

- **리릭 비디오 생성**  
  - 다운로드된 오디오, 앨범 아트, 번역된 가사를 MoviePy와 PIL을 이용해 합성하여 리릭 비디오를 생성합니다.

- **GUI 기반 작업 진행**  
  - PyQt6 기반의 인터페이스를 통해 사용자에게 검색 결과, 미리보기, 진행 상황 등을 실시간으로 제공합니다.

---

## 설치 및 환경 설정

### 1. 저장소 클론

```bash
git clone https://github.com/yourusername/LyricVideoMaker.git
cd LyricVideoMaker
```

### 2. 가상 환경 생성 (권장)

```bash
python -m venv venv
# Linux/MacOS
source venv/bin/activate
# Windows
venv\Scripts\activate
```

### 3. 필수 패키지 설치

프로젝트 루트에 있는 `requirements.txt` 파일을 사용하여 필요한 패키지를 설치합니다.

```bash
pip install -r requirements.txt
```

### 4. 환경 변수 설정

프로젝트 루트에 `.env` 파일을 생성하고 OpenAI API 키를 추가합니다.

```env
OPENAI_API_KEY=your_openai_api_key_here
```

---

## 사용법

### 1. 애플리케이션 실행

메인 스크립트인 `main.py`를 실행하여 애플리케이션을 시작합니다.

```bash
python main.py
```

PyQt6 기반의 GUI 창이 나타납니다.

### 2. 노래 검색 및 선택

- **검색 실행**  
  - 상단의 검색창에 노래 제목 또는 아티스트 이름을 입력한 후 **검색** 버튼을 클릭합니다.
  - Genie API와 YouTube에서 검색 결과가 각각 표시됩니다.

- **결과 선택**  
  - **Genie Music 결과**: 원하는 항목을 선택하면 제목, 아티스트, 앨범 아트 URL 등이 자동으로 입력 필드에 반영됩니다.
  - **YouTube 결과**: 원하는 영상을 선택하여 오디오 소스로 사용할 YouTube URL과 썸네일 정보가 설정됩니다.

- **앨범 아트 미리보기**  
  - 직접 앨범 아트 URL을 입력하거나, 검색 결과에서 선택하면 미리보기 창에 이미지가 표시됩니다.

### 3. 리릭 비디오 생성

- 모든 정보(노래 제목, 아티스트, 앨범 아트 URL, YouTube URL 등)를 확인한 후 **선택 완료 후 처리** 버튼을 클릭합니다.
- 순차적으로 아래 작업이 진행됩니다:
  - YouTube 오디오를 다운로드하여 MP3 파일 생성
  - 앨범 아트 이미지 다운로드
  - LRC 파일 파싱 및 OpenAI를 통한 가사 번역
  - MoviePy와 PIL을 이용한 리릭 비디오 생성
- 진행 상황은 별도의 창에서 실시간으로 표시되며, 최종 비디오 파일은 `output` 디렉토리에 저장됩니다.

---

## 코드 구조

- **main.py**  
  - PyQt6 GUI 및 전체 프로세스를 관리하는 메인 스크립트
- **album_art_finder.py**  
  - MusicBrainz와 Bugs를 이용한 앨범 아트 검색 및 다운로드 기능
- **genie_handler.py**  
  - Genie API를 통한 노래 검색, 가사 및 앨범 아트 URL 추출 기능
- **openai_handler.py**  
  - LRC 파일 파싱 및 OpenAI API를 통한 가사 번역 기능
- **process_manager.py**  
  - 오디오/앨범 아트 다운로드, 가사 번역, 비디오 생성 작업을 순차적으로 실행하는 모듈
- **ui_components.py**  
  - PyQt6 기반의 사용자 인터페이스 구성 요소 제공
- **video_maker.py**  
  - MoviePy, PIL, NumPy를 활용하여 리릭 비디오를 생성하는 모듈
- **youtube_handler.py**  
  - YouTube 검색 및 오디오 다운로드(yt-dlp 사용) 기능
- **genieapi**  
  - Genie Music API와의 연동을 위한 외부 패키지

---

## 문제 해결 및 지원

- 작업 진행 중 문제가 발생하면 콘솔에 출력되는 `[DEBUG]` 및 `[ERROR]` 메시지를 확인하세요.
- OpenAI API 키 및 기타 환경 설정이 올바른지 확인하시고, 필요시 GitHub 이슈를 통해 문의해 주세요.

---

## 라이선스

이 프로젝트는 **MIT 라이선스** 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참고하세요.
