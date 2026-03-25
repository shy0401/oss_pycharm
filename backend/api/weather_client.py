import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
SERVICE_KEY = os.getenv("PUBLIC_DATA_PORTAL_KEY")
BASE_URL = "http://apis.data.go.kr/1360000/MidFcstInfoService"

def get_base_tm_fc():
    """기상청 발표 시각(06:00, 18:00) 계산"""
    now = datetime.now()
    if now.hour < 6:
        return (now - timedelta(days=1)).strftime("%Y%m%d1800")
    elif now.hour < 18:
        return now.strftime("%Y%m%d0600")
    else:
        return now.strftime("%Y%m%d1800")

def fetch_kma_mid_term(land_reg_id: str, ta_reg_id: str):
    tm_fc = get_base_tm_fc()
    params = {
        'serviceKey': SERVICE_KEY,
        'dataType': 'JSON',
        'numOfRows': '10',
        'pageNo': '1',
        'tmFc': tm_fc
    }

    try:
        # 육상예보 및 기온조회 동시 호출
        l_res = requests.get(f"{BASE_URL}/getMidLandFc", params={**params, 'regId': land_reg_id}, timeout=10)
        t_res = requests.get(f"{BASE_URL}/getMidTa", params={**params, 'regId': ta_reg_id}, timeout=10)

        if l_res.status_code == 200 and t_res.status_code == 200:
            l_data, t_data = l_res.json(), t_res.json()
            if l_data['response']['header']['resultCode'] == '00':
                l_item = l_data['response']['body']['items']['item'][0]
                t_item = t_data['response']['body']['items']['item'][0]
                return {
                    "wf": l_item.get("wf3Am"),
                    "ta_min": t_item.get("taMin3"),
                    "ta_max": t_item.get("taMax3")
                }
    except Exception as e:
        print(f"API Error: {e}")
    return None