# 🌤️ Pastel Glass Weather Dashboard (실시간 기상/대기 통합 대시보드)

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.25+-FF4B4B.svg)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57.svg)

> **공공데이터포털(기상청, 에어코리아)**의 실시간 API를 활용하여 전국 주요 도시의 기상 현황과 대기질(미세먼지) 정보를 직관적으로 제공하는 웹 대시보드입니다. 최신 UI 트렌드인 **파스텔톤 글래스모피즘(Glassmorphism)** 디자인을 적용하여 사용자 경험(UX)을 극대화했습니다.

## ✨ 주요 기능 (Features)

* **🔐 안전한 인증 시스템:** JWT(JSON Web Token) 및 Bcrypt 해싱을 이용한 안전한 회원가입 및 로그인 기능.
* **🗺️ 실시간 기상/대기 통합 지도:** * Folium을 활용한 인터랙티브 한국 지도 구현 (화면 이탈 방지 적용).
  * 지역별 현재 기온, 습도, 강수확률을 한눈에 확인.
  * **대기질 상태에 따른 마커 색상 자동 변화** (좋음: 파스텔 그린, 보통: 베이지, 나쁨: 핑크, 매우나쁨: 다크그레이).
* **📅 주간 기상 예보 (Day 4 ~ Day 7):**
  * 기상청 중기예보 API 데이터를 수집(CSV)하여 지역별 4일~7일 후의 오전/오후 날씨, 강수확률, 최저/최고 기온 제공.
  * FontAwesome 아이콘을 활용한 직관적인 날씨 시각화.
* **🎨 글래스모피즘 UI/UX:** 부드러운 파스텔 그라데이션 배경과 반투명 유리 질감의 UI 요소 적용.

<br/>

## 🛠️ 기술 스택 (Tech Stack)

### Backend
* **Framework:** FastAPI
* **Database / ORM:** SQLite, SQLAlchemy
* **Security:** Passlib (Bcrypt), PyJWT
* **Data Parsing:** Requests, Pandas

### Frontend
* **Framework:** Streamlit
* **Map Visualization:** Folium, Streamlit-Folium
* **UI Design:** Custom HTML/CSS (Glassmorphism), FontAwesome

### Open APIs
* [기상청_단기예보 ((구)_동네예보) 조회서비스](https://www.data.go.kr/) (초단기실황, 단기예보)
* [기상청_중기예보 조회서비스](https://www.data.go.kr/) (중기육상예보, 중기기온예보)
* [한국환경공단_에어코리아_대기오염정보](https://www.data.go.kr/) (측정소별 실시간 측정정보)

<br/>

## 📂 프로젝트 구조 (Project Structure)

```text
📦 weather-dashboard
 ┣ 📂 backend
 ┃ ┣ 📂 api
 ┃ ┃ ┗ 📜 weather_client.py   # 기상청 & 에어코리아 API 호출 로직
 ┃ ┣ 📜 auth.py               # JWT 인증 및 보안 로직
 ┃ ┣ 📜 database.py           # SQLite DB 연결 및 세션 관리
 ┃ ┣ 📜 main.py               # FastAPI 메인 서버 (라우터)
 ┃ ┣ 📜 models.py             # SQLAlchemy 데이터베이스 모델
 ┃ ┗ 📜 schemas.py            # Pydantic 데이터 검증 스키마
 ┣ 📂 data
 ┃ ┣ 📜 weather.db            # 유저 정보 저장용 SQLite 데이터베이스
 ┃ ┗ 📜 weekly_forecast.csv   # 주간 예보 스냅샷 데이터
 ┣ 📂 frontend
 ┃ ┗ 📜 app.py                # Streamlit 메인 대시보드 UI
 ┣ 📜 fetch_to_csv.py         # 주간 예보 데이터 수집 배치 스크립트
 ┣ 📜 .env                    # 환경변수 (API Key, JWT Secret 등 - Github 업로드 X)
 ┗ 📜 README.md

🚀 설치 및 실행 방법 (Installation & Usage)

1. 환경 변수 설정

프로젝트 루트 디렉토리에 .env 파일을 생성하고 아래의 키를 입력합니다. (공공데이터포털에서 발급받은 Decoding 키를 사용해야 합니다.)

env
PUBLIC_DATA_PORTAL_KEY="본인의_기상청_디코딩_API_키"
AIRKOREA_API_KEY="본인의_에어코리아_디코딩_API_키"
JWT_SECRET_KEY="안전한_랜덤_문자열"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=60


2. 의존성 패키지 설치

pip install fastapi uvicorn sqlalchemy passlib bcrypt python-jose requests pandas folium streamlit streamlit-folium python-dotenv



3. 데이터 수집 (주간 예보)

메인 화면 하단의 주간 예보를 띄우기 위해 최초 1회 (또는 매일 정해진 시간에) 스크립트를 실행하여 CSV 데이터를 갱신합니다.
python fetch_to_csv.py



4. 서버 실행

프로젝트를 실행하려면 \*\*백엔드(FastAPI)\*\*와 프론트엔드(Streamlit) 서버를 각각 실행해야 합니다. 터미널을 두 개 열어주세요.

Terminal 1 (Backend):

bash
uvicorn backend.main:app --reload


  백엔드 서버가 http://127.0.0.1:8000 에서 실행됩니다.

Terminal 2 (Frontend):

bash
streamlit run frontend/app.py

프론트엔드 서버가 브라우저에 자동 팝업되며 http://localhost:8501 에서 실행됩니다.


👨‍💻 제작자 (Author)

  전북대학교 컴퓨터인공지능학부 OOO
  Email: white_shy@naver.com
  GitHub: [github.com/shy0401](https://github.com/shy0401/oss_pycharm)

