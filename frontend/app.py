import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
import pandas as pd
from datetime import datetime

# 1. 페이지 설정 및 세션 초기화
st.set_page_config(page_title="KMA Realtime Dashboard", layout="wide")

if "token" not in st.session_state: st.session_state.token = None
if "user_id" not in st.session_state: st.session_state.user_id = ""
if "weather_data" not in st.session_state: st.session_state.weather_data = None

BACKEND_URL = "http://127.0.0.1:8000"

# CSS: 기상청 스타일 테마
st.markdown("""
<style>
    .stApp { background-color: #f4f7f9; }
    .kma-box {
        background: white; padding: 25px; border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05); border-top: 5px solid #007bff;
        margin-bottom: 25px;
    }
    .kma-title { color: #333; font-weight: bold; font-size: 26px; }
</style>
""", unsafe_allow_html=True)

# --- [A] 로그인 화면 ---
if st.session_state.token is None:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="kma-box" style="text-align:center;"><h2>☀️ 중기 예보 시스템</h2></div>', unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["🔑 로그인", "📝 회원가입"])
        with tab1:
            with st.form("login"):
                uid = st.text_input("아이디")
                upw = st.text_input("비밀번호", type="password")
                if st.form_submit_button("로그인"):
                    try:
                        res = requests.post(f"{BACKEND_URL}/login", data={"username": uid, "password": upw})
                        if res.status_code == 200:
                            st.session_state.token = res.json()["access_token"]
                            st.session_state.user_id = uid
                            st.rerun()
                        else: st.error("로그인 정보가 올바르지 않습니다.")
                    except: st.error("서버 연결 실패")
        with tab2:
            with st.form("signup"):
                sid = st.text_input("새 아이디")
                spw = st.text_input("새 비밀번호", type="password")
                if st.form_submit_button("회원가입"):
                    res = requests.post(f"{BACKEND_URL}/signup", json={"username": sid, "password": spw})
                    if res.status_code == 201: st.success("가입 성공! 로그인해주세요.")
                    else: st.error("가입 실패")

# --- [B] 메인 대시보드 ---
else:
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user_id}님")
        if st.button("🚪 로그아웃"):
            st.session_state.token = None
            st.rerun()

    st.markdown('<div class="kma-box"><div class="kma-title">🗺️ 전국 실시간 기상/대기 정보 지도</div></div>', unsafe_allow_html=True)

    headers = {"Authorization": f"Bearer {st.session_state.token}"}

    # 자동 데이터 로드 (최초 1회)
    if st.session_state.weather_data is None:
        with st.spinner("🔄 기상청 및 에어코리아 실시간 정보를 가져오는 중..."):
            res = requests.get(f"{BACKEND_URL}/api/realtime-weather", headers=headers)
            if res.status_code == 200:
                st.session_state.weather_data = res.json()
                st.rerun()

    if st.session_state.weather_data:
        data_list = st.session_state.weather_data

        left_col, right_col = st.columns([7, 3])

        with left_col:
            # 한국 지도 고정 (max_bounds)
            m = folium.Map(
                location=[36.0, 127.8], zoom_start=7, tiles="CartoDB positron",
                max_bounds=True, min_zoom=7, max_zoom=10,
                bounds=[[33.0, 124.0], [39.0, 131.0]]
            )

            for d in data_list:
                temp = f"{d.get('temp', '?')}°"
                humi = f"{d.get('humi', '?')}%"
                pop = f"{d.get('pop', '?')}%"
                air_color = d.get('air_color', "#aaaaaa")
                air_status = d.get('air_status', "미수집")

                # 대형 반투명 원형 마커 (110px)
                folium.Marker(
                    [d['lat'], d['lon']],
                    icon=folium.DivIcon(html=f"""
                        <div style="
                            background-color: rgba(255, 255, 255, 0.7); 
                            border: 5px solid {air_color}; 
                            border-radius: 50%; width: 110px; height: 110px;
                            display: flex; flex-direction: column; align-items: center; justify-content: center;
                            box-shadow: 0 4px 10px rgba(0,0,0,0.15); font-family: sans-serif;
                        ">
                            <div style="font-size: 11px; color: #555;">{d['name']}</div>
                            <div style="font-size: 22px; font-weight: bold; color: #333;">{temp}</div>
                            <div style="font-size: 9px; color: #666;">습도:{humi} | 강수:{pop}</div>
                            <div style="font-size: 10px; font-weight: bold; color: {air_color}; margin-top:2px;">
                                {air_status}
                            </div>
                        </div>""")
                ).add_to(m)

            st_folium(m, width="100%", height=650)

        with right_col:
            st.markdown('<div class="kma-box"><h4>📊 실시간 상세 정보</h4></div>', unsafe_allow_html=True)
            df = pd.DataFrame(data_list)[['name', 'temp', 'humi', 'pop', 'air_status']]
            df.columns = ['지역', '온도', '습도', '강수확률', '대기상태']
            st.dataframe(df, hide_index=True, use_container_width=True)

            if st.button("🔄 실시간 수동 업데이트"):
                st.session_state.weather_data = None
                st.rerun()