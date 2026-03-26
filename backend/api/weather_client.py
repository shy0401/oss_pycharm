# backend/api/weather_client.py 전문

import os
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

# 인증키 로드 (반드시 Decoding 키)
KMA_SERVICE_KEY = os.getenv("PUBLIC_DATA_PORTAL_KEY")
AIR_SERVICE_KEY = os.getenv("AIRKOREA_API_KEY")

# API Base URLs
KMA_BASE_URL = "http://apis.data.go.kr/1360000"
AIR_BASE_URL = "http://apis.data.go.kr/B552584/ArpltnInforInqireSvc"

def _get_kma_base_time() -> Dict[str, str]:
    """초단기실황용 base_date, base_time 계산 (매시 45분 갱신)"""
    now = datetime.now()
    if now.minute < 45:
        # 45분 전이면 이전 시간 데이터 요청
        target = now - timedelta(hours=1)
        return {"date": target.strftime("%Y%m%d"), "time": target.strftime("%H00")}
    return {"date": now.strftime("%Y%m%d"), "time": now.strftime("%H00")}

def _get_vilage_base_time() -> Dict[str, str]:
    """단기예보용(강수확률) base_date, base_time 계산 (02, 05, 08... 3시간 간격)"""
    now = datetime.now()
    # 단기예보 발표 시간 (02:10, 05:10, 08:10 ...)
    base_times = [2, 5, 8, 11, 14, 17, 20, 23]

    current_hour = now.hour

    # 현재 시간보다 이전이면서 가장 가까운 발표 시간 찾기
    closer_time = 2
    for t in base_times:
        if current_hour >= t:
            closer_time = t
        else:
            break

    # 현재 시간이 발표 시간 + 10분 이전이면, 그 이전 base_time 사용
    if current_hour == closer_time and now.minute < 15:
        # 아주 기초적인 처리, 실제로는 어제 날짜로 넘어가야 할 수도 있음
        closer_time = base_times[base_times.index(closer_time)-1] if base_times.index(closer_time) > 0 else 23

    return {"date": now.strftime("%Y%m%d"), "time": f"{closer_time:02d}00"}


def fetch_realtime_weather(nx: int, ny: int, station: str) -> Optional[Dict[str, Any]]:
    """
    KMA 초단기실황, 단기예보, 에어코리아 미세먼지 API를 통합 호출
    """
    result = {
        "temp": None, "humi": None, # 초단기실황 (온도, 습도)
        "pop": None,               # 단기예보 (강수확률)
        "pm10": None, "pm25": None, # 에어코리아 (미세먼지)
        "air_status": "정보없음", "air_color": "#aaaaaa"
    }

    # 1. 기상청 초단기실황 (현재 온습도)
    kma_tm = _get_kma_base_time()
    params = {
        'serviceKey': KMA_SERVICE_KEY, 'dataType': 'JSON',
        'numOfRows': '10', 'pageNo': '1',
        'base_date': kma_tm["date"], 'base_time': kma_tm["time"],
        'nx': nx, 'ny': ny
    }

    try:
        res = requests.get(f"{KMA_BASE_URL}/VilageFcstInfoService_2.0/getUltraSrtNcst", params=params, timeout=5)
        if res.status_code == 200 and res.json()['response']['header']['resultCode'] == '00':
            items = res.json()['response']['body']['items']['item']
            for item in items:
                if item['category'] == 'T1H': result["temp"] = float(item['obsrValue']) # 기온
                if item['category'] == 'REH': result["humi"] = float(item['obsrValue']) # 습도
    except Exception as e: print(f"KMA Ncst Error: {e}")

    # 2. 기상청 단기예보 (강수확률 POP)
    vil_tm = _get_vilage_base_time()
    vil_params = {**params, 'base_date': vil_tm["date"], 'base_time': vil_tm["time"]}
    try:
        res = requests.get(f"{KMA_BASE_URL}/VilageFcstInfoService_2.0/getVilageFcst", params=vil_params, timeout=5)
        if res.status_code == 200 and res.json()['response']['header']['resultCode'] == '00':
            items = res.json()['response']['body']['items']['item']
            # 가장 가까운 시간의 POP 카테고리 찾기
            for item in items:
                if item['category'] == 'POP':
                    result["pop"] = int(item['fcstValue'])
                    break # 첫 번째 만나는 값이 가장 가까운 예보 시간
    except Exception as e: print(f"KMA Vilage Error: {e}")

    # 3. 에어코리아 미세먼지
    air_params = {
        'serviceKey': AIR_SERVICE_KEY, 'returnType': 'json',
        'numOfRows': '1', 'pageNo': '1',
        'stationName': station, 'dataTerm': 'DAILY', 'ver': '1.0'
    }
    try:
        res = requests.get(f"{AIR_BASE_URL}/getMsrstnAcctoRltmMesureDnsty", params=air_params, timeout=5)
        if res.status_code == 200:
            data = res.json()
            # 에어코리아는 resultCode가 에러시 영문으로 옴, 정상일 땐 response 하위에 body가 있음
            if 'response' in data and 'body' in data['response'] and data['response']['body']['totalCount'] > 0:
                item = data['response']['body']['items'][0]
                result["pm10"] = int(item['pm10Value']) if item['pm10Value'] and item['pm10Value'] != '-' else None
                result["pm25"] = int(item['pm25Value']) if item['pm25Value'] and item['pm25Value'] != '-' else None

                # 통합대기환경지수(khaiGrade) 기반 색상 설정 (가이드 82p)
                # 1:좋음(초록), 2:보통(노랑), import os
                # import requests
                # from datetime import datetime, timedelta
                # from typing import Dict, Any, Optional
                # from dotenv import load_dotenv
                #
                # # 환경 변수 로드 (.env 파일에 Decoding 키가 있어야 합니다)
                # load_dotenv()
                # KMA_SERVICE_KEY = os.getenv("PUBLIC_DATA_PORTAL_KEY")
                # AIR_SERVICE_KEY = os.getenv("AIRKOREA_API_KEY")
                #
                # # API Base URLs
                # KMA_BASE_URL = "http://apis.data.go.kr/1360000"
                # AIR_BASE_URL = "http://apis.data.go.kr/B552584/ArpltnInforInqireSvc"
                #
                # def _get_kma_base_time() -> Dict[str, str]:
                #     """초단기실황용 base_date, base_time 계산 (매시 45분 갱신)"""
                #     now = datetime.now()
                #     if now.minute < 45:
                #         # 45분 전이면 이전 시간 데이터 요청
                #         target = now - timedelta(hours=1)
                #         return {"date": target.strftime("%Y%m%d"), "time": target.strftime("%H00")}
                #     return {"date": now.strftime("%Y%m%d"), "time": now.strftime("%H00")}
                #
                # def _get_vilage_base_time() -> Dict[str, str]:
                #     """단기예보용(강수확률) base_date, base_time 계산 (02, 05, 08... 3시간 간격)"""
                #     now = datetime.now()
                #     # 단기예보 발표 시간
                #     base_times = [2, 5, 8, 11, 14, 17, 20, 23]
                #
                #     current_hour = now.hour
                #     closer_time = 2
                #
                #     for t in base_times:
                #         if current_hour >= t:
                #             closer_time = t
                #         else:
                #             break
                #
                #     # 발표 시간 + 10분 이전이면 이전 타임 적용
                #     if current_hour == closer_time and now.minute < 15:
                #         idx = base_times.index(closer_time)
                #         closer_time = base_times[idx - 1] if idx > 0 else 23
                #
                #     # 만약 closer_time이 23이고 현재가 새벽(0~2시)이라면 어제 날짜로 변경
                #     date_str = now.strftime("%Y%m%d")
                #     if current_hour < 2 and closer_time == 23:
                #         date_str = (now - timedelta(days=1)).strftime("%Y%m%d")
                #
                #     return {"date": date_str, "time": f"{closer_time:02d}00"}
                #
                #
                # def fetch_realtime_weather(nx: int, ny: int, station: str) -> Optional[Dict[str, Any]]:
                #     """
                #     KMA 초단기실황(온습도), KMA 단기예보(강수확률), 에어코리아(미세먼지)를 통합 호출합니다.
                #     """
                #     result = {
                #         "temp": None, "humi": None,
                #         "pop": None,
                #         "pm10": None, "pm25": None,
                #         "air_status": "정보없음", "air_color": "#aaaaaa"
                #     }
                #
                #     # 1. 기상청 초단기실황 (현재 온습도)
                #     kma_tm = _get_kma_base_time()
                #     params = {
                #         'serviceKey': KMA_SERVICE_KEY, 'dataType': 'JSON',
                #         'numOfRows': '20', 'pageNo': '1',
                #         'base_date': kma_tm["date"], 'base_time': kma_tm["time"],
                #         'nx': nx, 'ny': ny
                #     }
                #
                #     try:
                #         res = requests.get(f"{KMA_BASE_URL}/VilageFcstInfoService_2.0/getUltraSrtNcst", params=params, timeout=5)
                #         data = res.json()
                #         if data.get('response', {}).get('header', {}).get('resultCode') == '00':
                #             items = data['response']['body']['items']['item']
                #             for item in items:
                #                 if item['category'] == 'T1H': result["temp"] = item['obsrValue']
                #                 if item['category'] == 'REH': result["humi"] = item['obsrValue']
                #         else:
                #             print(f"⚠️ [초단기실황 에러] {station}: {data.get('response', {}).get('header', {}).get('resultMsg')}")
                #     except Exception as e:
                #         print(f"❌ [초단기실황 연결 실패] {station}: {e}")
                #
                #     # 2. 기상청 단기예보 (강수확률 POP)
                #     vil_tm = _get_vilage_base_time()
                #     vil_params = {**params, 'base_date': vil_tm["date"], 'base_time': vil_tm["time"]}
                #
                #     try:
                #         res = requests.get(f"{KMA_BASE_URL}/VilageFcstInfoService_2.0/getVilageFcst", params=vil_params, timeout=5)
                #         data = res.json()
                #         if data.get('response', {}).get('header', {}).get('resultCode') == '00':
                #             items = data['response']['body']['items']['item']
                #             for item in items:
                #                 if item['category'] == 'POP':
                #                     result["pop"] = item['fcstValue']
                #                     break # 첫 번째 만나는 값(가장 가까운 예보)만 사용
                #         else:
                #             print(f"⚠️ [단기예보 에러] {station}: {data.get('response', {}).get('header', {}).get('resultMsg')}")
                #     except Exception as e:
                #         print(f"❌ [단기예보 연결 실패] {station}: {e}")
                #
                #     # 3. 에어코리아 미세먼지 (PM10)
                #     air_params = {
                #         'serviceKey': AIR_SERVICE_KEY, 'returnType': 'json',
                #         'numOfRows': '1', 'pageNo': '1',
                #         'stationName': station, 'dataTerm': 'DAILY', 'ver': '1.0'
                #     }
                #
                #     try:
                #         res = requests.get(f"{AIR_BASE_URL}/getMsrstnAcctoRltmMesureDnsty", params=air_params, timeout=5)
                #         data = res.json()
                #
                #         # 에어코리아는 정상 응답 시 response.body 하위에 items가 존재함
                #         if 'response' in data and 'body' in data['response']:
                #             items = data['response']['body'].get('items', [])
                #             if items:
                #                 item = items[0]
                #                 result["pm10"] = item.get('pm10Value') if item.get('pm10Value') != '-' else None
                #                 result["pm25"] = item.get('pm25Value') if item.get('pm25Value') != '-' else None
                #
                #                 # 통합대기환경지수(khaiGrade) 기반 색상 설정
                #                 # 1:좋음(초록), 2:보통(노랑), 3:나쁨(빨강), 4:매우나쁨(검정)
                #                 grade = item.get('khaiGrade')
                #                 if grade == '1': result["air_status"], result["air_color"] = "좋음", "#00b050"
                #                 elif grade == '2': result["air_status"], result["air_color"] = "보통", "#ffff00"
                #                 elif grade == '3': result["air_status"], result["air_color"] = "나쁨", "#ff0000"
                #                 elif grade == '4': result["air_status"], result["air_color"] = "매우나쁨", "#000000"
                #         else:
                #             print(f"⚠️ [에어코리아 에러] {station}: 데이터 구조가 다름")
                #     except Exception as e:
                #         print(f"❌ [에어코리아 연결 실패] {station}: {e}")
                #
                #     return resultgit add .3:나쁨(빨강), 4:매우나쁨(검정)
                grade = item.get('khaiGrade')
                if grade == '1': result["air_status"], result["air_color"] = "좋음", "#00b050"
                elif grade == '2': result["air_status"], result["air_color"] = "보통", "#ffff00"
                elif grade == '3': result["air_status"], result["air_color"] = "나쁨", "#ff0000"
                elif grade == '4': result["air_status"], result["air_color"] = "매우나쁨", "#000000"
    except Exception as e: print(f"Airkorea Error: {e}")

    return result