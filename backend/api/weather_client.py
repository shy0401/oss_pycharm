import os
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()
KMA_SERVICE_KEY = os.getenv("PUBLIC_DATA_PORTAL_KEY")
AIR_SERVICE_KEY = os.getenv("AIRKOREA_API_KEY")

KMA_BASE_URL = "http://apis.data.go.kr/1360000"
AIR_BASE_URL = "http://apis.data.go.kr/B552584/ArpltnInforInqireSvc"

def _get_kma_base_time() -> Dict[str, str]:
    now = datetime.now()
    if now.minute < 45:
        target = now - timedelta(hours=1)
        return {"date": target.strftime("%Y%m%d"), "time": target.strftime("%H00")}
    return {"date": now.strftime("%Y%m%d"), "time": now.strftime("%H00")}

def _get_vilage_base_time() -> Dict[str, str]:
    now = datetime.now()
    base_times = [2, 5, 8, 11, 14, 17, 20, 23]
    current_hour = now.hour
    closer_time = 2

    for t in base_times:
        if current_hour >= t: closer_time = t
        else: break

    if current_hour == closer_time and now.minute < 15:
        idx = base_times.index(closer_time)
        closer_time = base_times[idx - 1] if idx > 0 else 23

    date_str = now.strftime("%Y%m%d")
    if current_hour < 2 and closer_time == 23:
        date_str = (now - timedelta(days=1)).strftime("%Y%m%d")

    return {"date": date_str, "time": f"{closer_time:02d}00"}

def fetch_realtime_weather(nx: int, ny: int, station: str) -> Optional[Dict[str, Any]]:
    result = {
        "temp": None, "humi": None, "pop": None,
        "pm10": None, "pm25": None,
        "air_status": "정보없음", "air_color": "#aaaaaa"
    }

    # 1. 기상청 초단기실황 (온도, 습도)
    kma_tm = _get_kma_base_time()
    params = {
        'serviceKey': KMA_SERVICE_KEY, 'dataType': 'JSON',
        'numOfRows': '20', 'pageNo': '1',
        'base_date': kma_tm["date"], 'base_time': kma_tm["time"],
        'nx': nx, 'ny': ny
    }
    try:
        res = requests.get(f"{KMA_BASE_URL}/VilageFcstInfoService_2.0/getUltraSrtNcst", params=params, timeout=5)
        data = res.json()
        if data.get('response', {}).get('header', {}).get('resultCode') == '00':
            items = data['response']['body']['items']['item']
            for item in items:
                if item['category'] == 'T1H': result["temp"] = item['obsrValue']
                if item['category'] == 'REH': result["humi"] = item['obsrValue']
    except Exception as e: print(f"KMA Ncst Error ({station}): {e}")

    # 2. 기상청 단기예보 (강수확률)
    vil_tm = _get_vilage_base_time()
    vil_params = {**params, 'base_date': vil_tm["date"], 'base_time': vil_tm["time"]}
    try:
        res = requests.get(f"{KMA_BASE_URL}/VilageFcstInfoService_2.0/getVilageFcst", params=vil_params, timeout=5)
        data = res.json()
        if data.get('response', {}).get('header', {}).get('resultCode') == '00':
            items = data['response']['body']['items']['item']
            for item in items:
                if item['category'] == 'POP':
                    result["pop"] = item['fcstValue']
                    break
    except Exception as e: print(f"KMA Vilage Error ({station}): {e}")

    # 3. 에어코리아 미세먼지
    air_params = {
        'serviceKey': AIR_SERVICE_KEY, 'returnType': 'json',
        'numOfRows': '1', 'pageNo': '1',
        'stationName': station, 'dataTerm': 'DAILY', 'ver': '1.0'
    }
    try:
        res = requests.get(f"{AIR_BASE_URL}/getMsrstnAcctoRltmMesureDnsty", params=air_params, timeout=5)
        data = res.json()
        if 'response' in data and 'body' in data['response']:
            items = data['response']['body'].get('items', [])
            if items:
                item = items[0]
                result["pm10"] = item.get('pm10Value') if item.get('pm10Value') != '-' else None
                result["pm25"] = item.get('pm25Value') if item.get('pm25Value') != '-' else None

                grade = item.get('khaiGrade')
                if grade == '1': result["air_status"], result["air_color"] = "좋음", "#00b050"
                elif grade == '2': result["air_status"], result["air_color"] = "보통", "#ffff00"
                elif grade == '3': result["air_status"], result["air_color"] = "나쁨", "#ff0000"
                elif grade == '4': result["air_status"], result["air_color"] = "매우나쁨", "#000000"
    except Exception as e: print(f"Airkorea Error ({station}): {e}")

    return result