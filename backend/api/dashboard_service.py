import os
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
KMA_KEY = os.getenv("PUBLIC_DATA_PORTAL_KEY") # 기상청 키
AIR_KEY = os.getenv("AIRKOREA_API_KEY") # 대기질 키 (없으면 KMA_KEY 사용)

KMA_BASE_URL = "http://apis.data.go.kr/1360000/VilageFcstInfoService_v2"
AIRKOREA_BASE_URL = "http://apis.data.go.kr/B552584/ArpltnInforInqireSvc"

def calculate_felt_temperature(T, RH, WS_ms):
    """체감온도 계산 함수 (간략화된 Humidex 공식 적용)"""
    T = float(T)
    RH = float(RH)
    # T (Celsius), RH (%)
    feel_t = T - ((100 - RH) / 5) # 매우 단순화된 예시, 정교한 공식 적용 권장
    return round(feel_t, 1)

def get_realtime_kma_data(nx, ny):
    """
    기상청 초단기실황 조회 (현재 기온, 습도, 풍속 등)
    - nx, ny: 기상청 격자 좌표
    """
    now = datetime.now()

    # [중요] 기상청 초단기실황은 매시 40분에 업데이트됩니다.
    # 40분 이전이면 '이전 시간'의 데이터를 조회해야 에러가 나지 않습니다.
    if now.minute < 40:
        now = now - timedelta(hours=1)

    base_date = now.strftime("%Y%m%d")
    base_time = now.strftime("%H00")

    url = f"{KMA_BASE_URL}/getUltraSrtNcst"

    # [주의] .env에 있는 'Decoding' 인증키를 사용하는 것이 가장 안정적입니다.
    params = {
        'serviceKey': KMA_KEY,
        'dataType': 'JSON',
        'base_date': base_date,
        'base_time': base_time,
        'nx': nx,
        'ny': ny,
        'pageNo': '1',
        'numOfRows': '20'
    }

    try:
        # 1. API 요청 실행
        res = requests.get(url, params=params, timeout=10)

        # [디버깅] 터미널에서 실제 요청 URL과 응답 내용을 확인하기 위함
        print(f"\n--- [KMA API DEBUG] ---")
        print(f"1. 요청 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"2. 대상 시간: {base_date} {base_time}")
        print(f"3. 응답 코드: {res.status_code}")

        # 만약 응답이 JSON이 아니라면(XML 에러 메시지 등) 여기서 힌트를 얻을 수 있습니다.
        if res.text.startswith("<"):
            print("⚠️ 경고: 기상청이 JSON 대신 XML(에러 메시지)을 보냈습니다.")
            print(f"응답 내용: {res.text}")
            return None, None, None

        # 2. JSON 파싱
        data_json = res.json()

        # 3. 데이터 구조 검사 (기상청 특유의 에러 메시지 처리)
        header = data_json.get('response', {}).get('header', {})
        if header.get('resultCode') != '00':
            print(f"❌ 기상청 비즈니스 에러: {header.get('resultMsg')} (코드: {header.get('resultCode')})")
            return None, None, None

        items_list = data_json.get('response', {}).get('body', {}).get('items', {}).get('item', [])

        if not items_list:
            print("⚠️ 데이터가 비어 있습니다. (해당 시간에 관측값이 아직 생성되지 않았을 수 있음)")
            return None, None, None

        # 4. 카테고리별 데이터 추출 (T1H: 기온, REH: 습도, WSD: 풍속 등)
        data = {item['category']: item['obsrValue'] for item in items_list}
        print(f"✅ 데이터 수집 성공: {data}")
        print(f"-----------------------\n")

        return data, base_date, base_time

    except requests.exceptions.RequestException as e:
        print(f"🌐 네트워크 연결 에러: {e}")
    except ValueError as e:
        print(f"🧠 JSON 파싱 에러 (데이터 형식이 잘못됨): {e}")
        print(f"응답 본문: {res.text}")
    except Exception as e:
        print(f"🔥 예상치 못한 에러: {e}")

    return None, None, None

def get_realtime_air_quality(station_name):
    """에어코리아 대기오염정보 조회 (PM10, PM2.5, O3 및 상태)"""
    url = f"{AIRKOREA_BASE_URL}/getMsrstnAcctoRltmMesureDnsty"
    params = {
        'serviceKey': AIR_KEY or KMA_KEY, 'dataType': 'JSON',
        'stationName': station_name, 'dataTerm': 'DAILY',
        'pageNo': '1', 'numOfRows': '10', 'returnType': 'json'
    }
    try:
        res = requests.get(url, params=params).json()
        items = res['response']['body']['items'][0] # 최신 1시간 데이터
        return {
            "pm10": items.get('pm10Value'), "pm25": items.get('pm25Value'),
            "o3": items.get('o3Value'), "pm10Grade": items.get('pm10Grade1h'),
            "pm25Grade": items.get('pm25Grade1h'), "o3Grade": items.get('o3Grade1h')
        }
    except Exception as e:
        print(f"AirQuality Error: {e}")
        return {
            "pm10": "N/A", "pm25": "N/A", "o3": "N/A", "pm10Grade": "0", "pm25Grade": "0", "o3Grade": "0"
        }

def get_integrated_dashboard_data(nx, ny, air_station, city_name):
    """모든 데이터를 통합하여 대시보드 JSON 반환"""
    kma_data, base_date, base_time = get_realtime_kma_data(nx, ny)
    if not kma_data: return None

    air_data = get_realtime_air_quality(air_station)

    felt_t = calculate_felt_temperature(kma_data['T1H'], kma_data['REH'], kma_data['WSD'])

    integrated_data = {
        "city": city_name,
        "observed_at": f"{base_date} {base_time}",
        "current": {
            "T1H": kma_data['T1H'],
            "FeltT": felt_t,
            "REH": kma_data['REH'],
            "WSD": kma_data['WSD'],
            # 날씨 상태 아이콘 코드는 단기예보 API 호출 필요 (여기선 생략)
        },
        "air": air_data
        # 시간별 예보 테이블 데이터는 단기예보 API 호출 필요 (여기선 생략)
    }
    return integrated_data