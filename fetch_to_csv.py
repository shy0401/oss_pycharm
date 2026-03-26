import os
import requests
import pandas as pd
from datetime import datetime, timedelta

# .env 파일에서 키를 로드하는 방식을 유지하는 것을 권장합니다.
SERVICE_KEY = "4bbb4cd336fcd53b9d713970e85cd967c48d9421d06a90ec7755f0315e6620d0"
BASE_URL = "http://apis.data.go.kr/1360000/MidFcstInfoService"

# 전주(11F10201)를 포함한 주요 타겟 지역 설정
REGION_CONFIG = [
    {"name": "서울", "land": "11B00000", "ta": "11B10101"},
    {"name": "전주", "land": "11F10000", "ta": "11F10201"},
    {"name": "대전", "land": "11C20000", "ta": "11C20401"},
    {"name": "광주", "land": "11F20000", "ta": "11F20501"},
    {"name": "부산", "land": "11H20000", "ta": "11H20201"},
    {"name": "울산", "land": "11H20000", "ta": "11H20101"}
]

def get_base_tm_fc():
    """발표 시각(tmFc) 생성: 06시, 18시 기준"""
    now = datetime.now()
    if now.hour < 6:
        return (now - timedelta(days=1)).strftime("%Y%m%d1800")
    elif now.hour < 18:
        return now.strftime("%Y%m%d0600")
    else:
        return now.strftime("%Y%m%d1800")

def fetch_weekly_forecast():
    tm_fc = get_base_tm_fc()
    all_results = []
    print(f"🚀 주간 예보 수집 시작 (발표시각: {tm_fc})")

    for r in REGION_CONFIG:
        params = {
            'serviceKey': SERVICE_KEY,
            'dataType': 'JSON',
            'numOfRows': '10',
            'pageNo': '1',
            'tmFc': tm_fc
        }

        try:
            # 육상예보(강수, 날씨) 및 기온예보 동시 호출
            l_res = requests.get(f"{BASE_URL}/getMidLandFcst", params={**params, 'regId': r['land']}, timeout=10)
            t_res = requests.get(f"{BASE_URL}/getMidTa", params={**params, 'regId': r['ta']}, timeout=10)

            l_data = l_res.json()
            t_data = t_res.json()

            if l_data['response']['header']['resultCode'] == '00':
                l_item = l_data['response']['body']['items']['item'][0]
                t_item = t_data['response']['body']['items']['item'][0]

                # 4일~7일차 데이터 추출 구조화
                for day in range(4, 8):
                    all_results.append({
                        "지역": r["name"],
                        "예보일": (datetime.now() + timedelta(days=day)).strftime("%Y-%m-%d"),
                        "오전날씨": l_item.get(f"wf{day}Am", "정보없음"),
                        "오후날씨": l_item.get(f"wf{day}Pm", "정보없음"),
                        "오전강수확률": l_item.get(f"rnSt{day}Am", 0),
                        "오후강수확률": l_item.get(f"rnSt{day}Pm", 0),
                        "최저기온": t_item.get(f"taMin{day}", 0),
                        "최고기온": t_item.get(f"taMax{day}", 0)
                    })
                print(f"✅ {r['name']} 주간 수집 완료")

        except Exception as e:
            print(f"❌ {r['name']} 처리 오류: {e}")

    # CSV 저장 (프론트엔드에서 읽기 쉬운 형태로 평탄화)
    if all_results:
        df = pd.DataFrame(all_results)
        os.makedirs("./data", exist_ok=True)
        df.to_csv("./data/weekly_forecast.csv", index=False, encoding="utf-8-sig")
        print(f"\n✨ 완료! 총 {len(all_results)}건 데이터 저장됨: ./data/weekly_forecast.csv")

if __name__ == "__main__":
    fetch_weekly_forecast()