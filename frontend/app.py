import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
import pandas as pd

# 1. 세션 상태 초기화 (가장 먼저 실행)
if "token" not in st.session_state:
    st.session_state.token = None
if "user_id" not in st.session_state:
    st.session_state.user_id = ""

st.set_page_config(page_title="KMA Weather Dashboard", layout="wide")

# CSS: 기상청 스타일 커스텀
st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    .weather-box {
        background: white; padding: 20px; border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08); border-top: 6px solid #007bff;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

BACKEND_URL = "http://127.0.0.1:8000"

# --- [A] 로그인 및 회원가입 화면 (token이 없을 때) ---
if st.session_state.token is None:
    st.markdown('<div class="weather-box" style="text-align:center;"><h1>☀️ 중기 예보 시스템</h1><p>서비스 이용을 위해 로그인해주세요.</p></div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["🔑 로그인", "📝 회원가입"])

    with tab1: # 로그인 로직
        with st.form("login_form"):
            uid = st.text_input("아이디")
            upw = st.text_input("비밀번호", type="password")
            if st.form_submit_button("로그인"):
                try:
                    # FastAPI OAuth2 표준에 따라 data= (Form-data) 형식을 사용합니다.
                    res = requests.post(f"{BACKEND_URL}/login", data={"username": uid, "password": upw})
                    if res.status_code == 200:
                        st.session_state.token = res.json()["access_token"]
                        st.session_state.user_id = uid
                        st.success("로그인 성공! 대시보드로 이동합니다.")
                        st.rerun() # 페이지를 즉시 다시 그려서 [B] 화면으로 이동시킴
                    else:
                        st.error("아이디 또는 비밀번호가 틀렸습니다.")
                except requests.exceptions.ConnectionError:
                    st.error("🔌 백엔드 서버 연결 실패 (8000번 포트를 확인하세요).")

    with tab2: # 회원가입 로직
        with st.form("signup_form"):
            new_uid = st.text_input("아이디 생성")
            new_upw = st.text_input("비밀번호 생성", type="password")
            confirm_upw = st.text_input("비밀번호 확인", type="password")
            if st.form_submit_button("회원가입 완료"):
                if new_upw != confirm_upw:
                    st.error("비밀번호가 서로 일치하지 않습니다.")
                else:
                    try:
                        # 회원가입은 json= 형식을 사용합니다.
                        res = requests.post(f"{BACKEND_URL}/signup", json={"username": new_uid, "password": new_upw})
                        if res.status_code == 201:
                            st.success("회원가입이 완료되었습니다! 로그인 탭에서 접속해주세요.")
                        else:
                            st.error(res.json().get("detail", "회원가입 실패"))
                    except:
                        st.error("서버 연결 실패")

# --- [B] 메인 대시보드 화면 (token이 있을 때) ---
else:
    # 사이드바 설정
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user_id}님")
        if st.button("🚪 로그아웃"):
            st.session_state.token = None
            st.session_state.user_id = ""
            st.rerun()

    st.markdown('<div class="weather-box"><h2>🗺️ 전국 주요 지역 중기 예보</h2></div>', unsafe_allow_html=True)

    headers = {"Authorization": f"Bearer {st.session_state.token}"}

    # 1. 데이터 동기화 기능
    col1, col2 = st.columns([2, 8])
    with col1:
        if st.button("🔄 날씨 동기화"):
            with st.spinner("기상청 데이터 수집 중..."):
                requests.post(f"{BACKEND_URL}/api/sync-weather", headers=headers)
                st.rerun()

    # 2. 데이터 로드 및 지도 시각화
    try:
        res = requests.get(f"{BACKEND_URL}/api/forecasts", headers=headers)
        if res.status_code == 200:
            weather_data = res.json().get("data", [])
            weather_dict = {d['region_name']: d for d in weather_data}

            left_col, right_col = st.columns([7, 3])

            with left_col:
                # 지도 렌더링
                m = folium.Map(location=[36.3, 127.8], zoom_start=7, tiles="CartoDB positron")

                # 가이드 기준 6개 지역 (서울, 대전, 전주, 광주, 부산, 울산) [cite: 74, 78]
                default_regions = [
                    ("서울", 37.56, 126.97), ("대전", 36.35, 127.38), ("전주", 35.82, 127.14),
                    ("광주", 35.15, 126.85), ("부산", 35.17, 129.07), ("울산", 35.53, 129.31)
                ]

                for name, lat, lon in default_regions:
                    data = weather_dict.get(name)
                    temp = f"{int(data['ta_max'])}°" if data else "?°"
                    color = "#FF4B4B" if data and data.get('ta_max', 0) > 15 else "#1C83E1"

                    folium.Marker(
                        [lat, lon],
                        icon=folium.DivIcon(html=f"""
                            <div style="background-color: white; border: 3px solid {color}; border-radius: 50%; 
                            width: 45px; height: 45px; display: flex; flex-direction: column; align-items: center; 
                            justify-content: center; font-size: 11px; font-weight: bold; box-shadow: 2px 2px 5px rgba(0,0,0,0.2);">
                                <div style="color: black;">{temp}</div>
                                <div style="font-size: 8px; color: #666;">{name}</div>
                            </div>"""),
                    ).add_to(m)
                st_folium(m, width="100%", height=600)

            with right_col:
                st.markdown('<div class="weather-box"><h4>📊 지역별 상세</h4></div>', unsafe_allow_html=True)
                if weather_data:
                    df = pd.DataFrame(weather_data)
                    st.dataframe(df[['region_name', 'wf_status', 'ta_max']], hide_index=True)
                else:
                    st.info("데이터가 없습니다. 동기화를 클릭하세요.")
        else:
            st.error("세션이 만료되었습니다. 다시 로그인해주세요.")
            st.session_state.token = None
            st.rerun()
    except Exception as e:
        st.error(f"데이터 로딩 중 오류 발생: {e}")