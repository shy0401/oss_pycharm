import os
import requests
import pandas as pd
from datetime import datetime, timedelta

# [중요] 공공데이터포털 상세페이지에서 [일반 인증키(Decoding)]을 복사해서 넣으세요.
SERVICE_KEY = "4bbb4cd336fcd53b9d713970e85cd967c48d9421d06a90ec7755f0315e6620d0"
BASE_URL = "http://apis.data.go.kr/1360000/MidFcstInfoService"

# 가이드 문서(25, 74, 78페이지) 기준 정확한 코드 적용 [cite: 14, 74, 78]
REGION_CONFIG = [
    {"name": "서울", "land": "11B00000", "ta": "11B10101", "lat": 37.56, "lon": 126.97},
    {"name": "전주", "land": "11F10000", "ta": "11F10201", "lat": 35.82, "lon": 127.14}, # 지점코드 수정
    {"name": "대전", "land": "11C20000", "ta": "11C20401", "lat": 36.35, "lon": 127.38},
    {"name": "광주", "land": "11F20000", "ta": "11F20501", "lat": 35.15, "lon": 126.85},
    {"name": "부산", "land": "11H20000", "ta": "11H20201", "lat": 35.17, "lon": 129.07},
    {"name": "울산", "land": "11H20000", "ta": "11H20101", "lat": 35.53, "lon": 129.31}
]

def get_base_tm_fc():
    now = datetime.now()
    # 06:00, 18:00 발표 기준 (최근 24시간 자료만 제공) [cite: 27]
    if now.hour < 6:
        return (now - timedelta(days=1)).strftime("%Y%m%d1800")
    elif now.hour < 18:
        return now.strftime("%Y%m%d0600")
    else:
        return now.strftime("%Y%m%d1800")

def fetch_all_to_csv():
    tm_fc = get_base_tm_fc()
    all_results = []
    print(f"🚀 수집 시작 (발표시각: {tm_fc})")

    for r in REGION_CONFIG:
        params = {
            'serviceKey': SERVICE_KEY,
            'dataType': 'JSON', # JSON 형식 요청
            'numOfRows': '10',
            'pageNo': '1',
            'tmFc': tm_fc
        }

        try:
            # 1. 중기육상예보조회 호출 [cite: 36]
            l_res = requests.get(f"{BASE_URL}/getMidLandFcst", params={**params, 'regId': r['land']}, timeout=10)
            # 2. 중기기온조회 호출 [cite: 48]
            t_res = requests.get(f"{BASE_URL}/getMidTa", params={**params, 'regId': r['ta']}, timeout=10)

            # JSON 파싱 전 응답 확인 (에러 시 XML이 올 수 있음) [cite: 33, 87]
            if l_res.text.startswith("<") or t_res.text.startswith("<"):
                print(f"⚠️ {r['name']} 서버 응답 에러: {l_res.text[:150]}")
                continue

            l_data = l_res.json()
            t_data = t_res.json()

            if l_data['response']['header']['resultCode'] == '00':
                l_item = l_data['response']['body']['items']['item'][0]
                t_item = t_data['response']['body']['items']['item'][0]

                all_results.append({
                    "region_name": r["name"], "lat": r["lat"], "lon": r["lon"],
                    "wf_status": l_item.get("wf3Am") or l_item.get("wf5Am"), # 발표 시각에 따른 데이터 추출 [cite: 41]
                    "ta_min": t_item.get("taMin3") or t_item.get("taMin5"),
                    "ta_max": t_item.get("taMax3") or t_item.get("taMax5"),
                    "land_reg_id": r["land"], "ta_reg_id": r["ta"]
                })
                print(f"✅ {r['name']} 수집 완료")
            else:
                print(f"❌ {r['name']} API 에러: {l_data['response']['header']['resultMsg']}")

        except Exception as e:
            print(f"❌ {r['name']} 처리 중 오류: {e}")

    if all_results:
        df = pd.DataFrame(all_results)
        if not os.path.exists("./data"): os.makedirs("./data")
        df.to_csv("./data/weather_data.csv", index=False, encoding="utf-8-sig")
        print(f"\n✨ 완료! 총 {len(all_results)}건 저장되었습니다.")
    else:
        print("\n😭 수집된 데이터가 없습니다. 인증키 활성화(1~2시간)를 기다려주세요.")

if __name__ == "__main__":
    fetch_all_to_csv()