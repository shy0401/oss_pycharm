import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
import pandas as pd
from datetime import datetime, timedelta
import os

# 1. 페이지 설정 및 세션 초기화
st.set_page_config(page_title="Pastel Glass Weather Dashboard", layout="wide")

if "token" not in st.session_state: st.session_state.token = None
if "user_id" not in st.session_state: st.session_state.user_id = ""
if "weather_data" not in st.session_state: st.session_state.weather_data = None
# 주간 예보 데이터를 저장할 새로운 세션 변수
if "weekly_forecast_data" not in st.session_state: st.session_state.weekly_forecast_data = None

BACKEND_URL = "http://127.0.0.1:8000"

# --- [개선된 CSS] Turn 11의 포근한 파스텔 + 완벽한 Glassmorphism ---
st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    
    * { font-family: 'Pretendard', sans-serif; }

    /* 1. 전체 앱 배경 (파스텔 민트 & 라벤더 그라데이션) */
    .stApp { 
        background: linear-gradient(135deg, #E2ECE9 0%, #F0E5E9 100%);
        background-attachment: fixed;
    }
    
    /* 2. 사이드바 디자인 (소프트 라벤더) */
    [data-testid="stSidebar"] {
        background: rgba(240, 229, 233, 0.45) !important;
        backdrop-filter: blur(10px) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.3) !important;
    }

    /* 3. 파스텔 글래스 박스 (메인 카드) */
    .glass-box {
        background: rgba(255, 255, 255, 0.55);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.7);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
        padding: 25px;
        margin-bottom: 20px;
        color: #2C3E50;
    }
    
    /* 타이틀 디자인 */
    .glass-title { 
        font-weight: 800; font-size: 32px; color: #4A6572;
        margin-bottom: 10px;
        letter-spacing: -1px;
    }

    /* 버튼 파스텔 커스텀 */
    .stButton>button {
        background: rgba(255, 255, 255, 0.3) !important;
        color: #4A6572 !important;
        border: 1px solid rgba(255, 255, 255, 0.6) !important;
        border-radius: 12px !important;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background: rgba(255, 255, 255, 0.5) !important;
        transform: scale(1.02);
    }

    /* 탭 스타일 수정 */
    .stTabs [data-baseweb="tab-list"] {
        background-color: transparent; gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        background-color: rgba(255, 255, 255, 0.3);
        border-radius: 10px; color: #4A6572; padding: 0px 20px;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: rgba(255, 255, 255, 0.6);
    }
</style>
""", unsafe_allow_html=True)


# --- [A] 로그인 및 회원가입 화면 ---
if st.session_state.token is None:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown('''
            <div class="glass-box" style="text-align:center;">
                <div class="glass-title">🌤️ Weather Dashboard</div>
                <p style="color:#6B7C93; font-weight:500;">포근한 파스텔 날씨 예보 시스템</p>
            </div>
        ''', unsafe_allow_html=True)

        tab1, tab2 = st.tabs(["🔒 LOGIN", "📝 JOIN"])

        with tab1: # 로그인 영역 (즉시 리런 로직 통합)
            with st.form(key="login_form"):
                uid = st.text_input("아이디")
                upw = st.text_input("비밀번호", type="password")
                if st.form_submit_button("시작하기", use_container_width=True):
                    try:
                        res = requests.post(f"{BACKEND_URL}/login", data={"username": uid, "password": upw})
                        if res.status_code == 200:
                            st.session_state.token = res.json()["access_token"]
                            st.session_state.user_id = uid
                            st.rerun() # 로그인 성공 시 즉시 페이지 전환
                        else: st.error("❌ 로그인 정보가 일치하지 않습니다.")
                    except: st.error("🔌 서버 연결 실패 (백엔드를 확인하세요)")

        with tab2: # 회원가입 영역
            with st.form(key="signup_form"):
                sid = st.text_input("새 아이디")
                spw = st.text_input("새 비밀번호", type="password")
                if st.form_submit_button("가입 완료", use_container_width=True):
                    try:
                        res = requests.post(f"{BACKEND_URL}/signup", json={"username": sid, "password": spw})
                        if res.status_code == 201: st.success("🎉 가입 성공! 로그인 해주세요.")
                        else: st.error(res.json().get("detail", "가입 실패"))
                    except: st.error("서버 연결 실패")

# --- [B] 메인 대시보드 화면 ---
else:
    #
    # 헬퍼 함수: 날씨 상태에 따른 FontAwesome 아이콘 매핑 (더 정교하게 수정)
    def get_weather_icon(wf_status):
        # 기상청이 보내주는 다양한 상태 정보를 모두 커버하도록 보강합니다.
        icons = {
            # 1. 기본 상태
            "맑음": "fa-sun",
            "구름많음": "fa-cloud-sun",
            "흐림": "fa-cloud",

            # 2. 비 (강수확률에 따라 아이콘 강도 조절)
            "비": "fa-cloud-showers-heavy",
            "약한비": "fa-cloud-rain",
            "강한비": "fa-cloud-showers-heavy",

            # 3. 눈
            "눈": "fa-snowflake",
            "약한눈": "fa-snowflake",
            "강한눈": "fa-snowflake",

            # 4. 혼합 및 예외 상황
            "비/눈": "fa-cloud-meatball",
            "소나기": "fa-cloud-showers-heavy",
            "천둥번개": "fa-bolt",
            "안개": "fa-smog",
            "박무": "fa-smog", # 옅은 안개

            # 5. [추가] 복합 상태 (기상청 API에서 흔히 발생)
            "구름많고 비": "fa-cloud-sun-rain",
            "흐리고 비": "fa-cloud-showers-heavy",
            "구름많고 눈": "fa-cloud-snow",
            "흐리고 눈": "fa-cloud-snow"
        }
        # 데이터를 찾지 못했을 때 'fa-question' 대신 기본 아이콘('fa-cloud')을 반환하도록 수정
        return icons.get(wf_status, "fa-cloud")

    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user_id}님")
        st.write(f"오늘 접속: {datetime.now().strftime('%m월 %d일 %H:%M')}")
        st.divider()
        if st.button("🚪 로그아웃", use_container_width=True):
            st.session_state.token, st.session_state.weather_data, st.session_state.weekly_forecast_data = None, None, None
            st.rerun()

    st.markdown('<div class="glass-box"><div class="glass-title">🗺️ 전국 실시간 통합 관측 지도</div></div>', unsafe_allow_html=True)
    headers = {"Authorization": f"Bearer {st.session_state.token}"}

    # 데이터 자동 동기화 (세션에 데이터가 없을 때)
    if st.session_state.weather_data is None:
        with st.spinner("부드러운 날씨 데이터를 가져오고 있어요..."):
            try:
                res = requests.get(f"{BACKEND_URL}/api/realtime-weather", headers=headers)
                if res.status_code == 200:
                    st.session_state.weather_data = res.json()
                    st.rerun()
            except: st.error("데이터 동기화 실패")

    if st.session_state.weather_data:
        data_list = st.session_state.weather_data
        left_col, right_col = st.columns([7, 3])

        with left_col:
            # 지도 렌더링
            m = folium.Map(
                location=[36.2, 127.8], zoom_start=7, tiles="CartoDB positron",
                max_bounds=True, min_zoom=7, max_zoom=10,
                bounds=[[33.0, 124.0], [39.0, 131.0]]
            )
            for d in data_list:
                temp = f"{d.get('temp', '?')}°"
                air_color = d.get('air_color', "#aaaaaa")
                air_status = d.get('air_status', "미수집")

                text_color = "white" if air_color == "#000000" else "black"

                # [수정됨] 마커 크기 75px로 축소 및 내부 폰트 사이즈 조정
                folium.Marker(
                    [d['lat'], d['lon']],
                    icon=folium.DivIcon(html=f"""
                        <div style="
                            background: rgba(255, 255, 255, 0.6); 
                            backdrop-filter: blur(8px); 
                            border: 3px solid {air_color}; 
                            border-radius: 50%; 
                            width: 75px; height: 75px; /* 크기 대폭 축소 */
                            display: flex; flex-direction: column; align-items: center; justify-content: center;
                            box-shadow: 0 4px 15px rgba(0,0,0,0.05); font-family: sans-serif;
                        ">
                            <div style="font-size: 10px; color: #4A6572; font-weight: bold; text-shadow: 1px 1px 1px rgba(255,255,255,0.7);">{d['name']}</div>
                            <div style="font-size: 18px; font-weight: 800; color: #2C3E50; margin: -2px 0;">{temp}</div>
                            <div style="font-size: 9px; font-weight: bold; color: {text_color}; background: {air_color}; 
                                        padding: 2px 5px; border-radius: 8px; margin-top:2px;">
                                {air_status}
                            </div>
                        </div>""")
                ).add_to(m)

            st_folium(m, width="100%", height=650)

        with right_col:
            st.markdown('<div class="glass-box"><div style="font-weight:700; font-size:20px; color:#4A6572; margin-bottom:10px;">📊 실시간 관측 현황</div>', unsafe_allow_html=True)
            df = pd.DataFrame(data_list)[['name', 'temp', 'humi', 'pop', 'air_status']]
            df.columns = ['지역', '온도', '습도', '강수', '대기']
            st.dataframe(df, hide_index=True, use_container_width=True)

            if st.button("🔄 실시간 수동 업데이트", use_container_width=True):
                st.session_state.weather_data = None
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)


    # --- [C] 하단 주간 예보 영역 (csv 데이터를 활용한 표 출력) ---
    st.divider()
    st.markdown('<div class="glass-box"><div class="glass-title">📅 주간 기상 예보 (Day 4~7)</div></div>', unsafe_allow_html=True)

    csv_path = "./data/weekly_forecast.csv"
    if not os.path.exists(csv_path):
        st.warning("⚠️ 주간 예보 데이터(`weekly_forecast.csv`)가 없습니다. 수집 스크립트(`fetch_to_csv.py`)를 먼저 실행해주세요.")
    else:
        # 데이터 로드 및 전처리
        weekly_df = pd.read_csv(csv_path)
        regions = weekly_df['지역'].unique()

        selected_region = st.selectbox("조회할 지역을 선택하세요", regions, index=1) # 전주를 기본값으로

        region_forecast = weekly_df[weekly_df['지역'] == selected_region].reset_index(drop=True)

        # 주간 예보 카드를 가로로 배치 (날씨누리 UI 스타일)
        cols = st.columns(len(region_forecast))

        for idx, col in enumerate(cols):
            row = region_forecast.iloc[idx]

            # 오전/오후 날씨 아이콘 선택
            icon_am = get_weather_icon(row['오전날씨'])
            icon_pm = get_weather_icon(row['오후날씨'])

            # 날씨 정보 텍스트 (같으면 하나만, 다르면 묶어서 표시)
            weather_desc = row['오전날씨'] if row['오전날씨'] == row['오후날씨'] else f"오전 {row['오전날씨']} / 오후 {row['오후날씨']}"

            # 예보일 가독성 향상
            forecast_date = datetime.strptime(row['예보일'], "%Y-%m-%d")
            date_str = forecast_date.strftime("%m월 %d일")

            with col:
                # [핵심] FontAwesome 아이콘을 활용한 주간 예보 카드
                #
                st.markdown(f"""
                <div class="glass-box" style="text-align: center; border-radius: 12px; padding: 20px;">
                    <p style="font-size:1.1em; font-weight:700; color:#4A6572; margin-bottom:5px;">{date_str} (D+{idx+4})</p>
                    <div style="font-size:2em; color: #4A6572; margin: 10px 0;">
                        <i class="fas {icon_am}" title="오전: {row['오전날씨']}"></i>
                        <span style="font-size: 0.6em; color: #aaaaaa;">/</span>
                        <i class="fas {icon_pm}" title="오후: {row['오후날씨']}"></i>
                    </div>
                    <p style="font-weight:700; color:#2C3E50; margin: 5px 0;">{weather_desc}</p>
                    <p style="font-size: 1.2em; font-weight: bold;">
                        <span style="color:#1976d2;">{row['최저기온']}°C</span> / <span style="color:#d32f2f;">{row['최고기온']}°C</span>
                    </td>
                    <p style="font-size: 0.9em; color: #0288d1; margin-top:5px;">☔ 강수확률 {row['오전강수확률']}%</p>
                </div>
                """, unsafe_allow_html=True)

    # FontAwesome 아이콘 폰트를 화면에 로드합니다 (fbcorn가 아닌 fa를 사용합니다)
    st.markdown('<link rel="stylesheet" href="https://use.fontawesome.com/releases/v5.15.4/css/all.css">', unsafe_allow_html=True)