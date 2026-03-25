import os
import pandas as pd
from sqlalchemy.orm import Session
from datetime import datetime
from . import models

CSV_FILE_PATH = "./data/data.csv"

def load_csv_to_db(db: Session):
    """
    서버 시작 시 CSV 파일을 읽어 SQLite DB에 초기 데이터를 적재합니다.
    """
    # 1. 파일 존재 여부 확인
    if not os.path.exists(CSV_FILE_PATH):
        print(f"⚠️ 경고: {CSV_FILE_PATH} 파일을 찾을 수 없습니다. 데이터 적재를 건너뜁니다.")
        return

    # 2. 이미 데이터가 있는지 확인 (데이터 중복 방지)
    existing_count = db.query(models.MidTermForecast).count()
    if existing_count > 0:
        print(f"✅ DB에 이미 {existing_count}개의 예보 데이터가 존재합니다. 적재를 건너뜁니다.")
        return

    # 3. CSV 읽기 및 DB 적재
    print("⏳ CSV 파일에서 데이터를 읽어 DB에 적재를 시작합니다...")
    try:
        df = pd.read_csv(CSV_FILE_PATH)

        records_to_insert = []
        for _, row in df.iterrows():
            # 날짜 문자열(예: '2026-03-20')을 Python Date 객체로 변환
            f_date = datetime.strptime(str(row['forecast_date']), "%Y-%m-%d").date()

            record = models.MidTermForecast(
                reg_id=str(row['reg_id']),
                region_name=str(row['region_name']),
                lat=float(row['lat']),
                lon=float(row['lon']),
                forecast_date=f_date,
                ta_min=float(row['ta_min']),
                ta_max=float(row['ta_max'])
            )
            records_to_insert.append(record)

        # bulk_save_objects를 쓰면 수천 건의 데이터도 1초 만에 들어갑니다.
        db.bulk_save_objects(records_to_insert)
        db.commit()
        print(f"🎉 총 {len(records_to_insert)}건의 데이터가 성공적으로 적재되었습니다!")

    except Exception as e:
        db.rollback()
        print(f"❌ 데이터 적재 중 오류 발생: {e}")