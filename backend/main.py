import pandas as pd
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
from typing import List, Dict, Any

from . import models, schemas, auth, database
from .api.weather_client import fetch_realtime_weather

# 전주를 비롯한 주요 도시 매핑
REALTIME_REGION_CONFIG = [
    {"name": "서울", "nx": 60, "ny": 127, "station": "종로구", "lat": 37.5665, "lon": 126.9780},
    {"name": "대전", "nx": 67, "ny": 100, "station": "정림동", "lat": 36.3504, "lon": 127.3845},
    {"name": "전주", "nx": 63, "ny": 89,  "station": "삼천동", "lat": 35.8242, "lon": 127.1480},
    {"name": "광주", "nx": 58, "ny": 74,  "station": "농성동", "lat": 35.1595, "lon": 126.8526},
    {"name": "부산", "nx": 98, "ny": 76,  "station": "광복동", "lat": 35.1796, "lon": 129.0756},
    {"name": "울산", "nx": 102, "ny": 84, "station": "신정동", "lat": 35.5384, "lon": 129.3114}
]

@asynccontextmanager
async def lifespan(app: FastAPI):
    models.Base.metadata.create_all(bind=database.engine)
    yield

app = FastAPI(title="KMA Realtime Weather API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# backend/main.py 수정 부분

@app.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    """새로운 사용자를 등록합니다."""
    # 1. 중복 사용자 확인
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        # 중복 시 400 에러와 함께 상세 메시지 전달
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{user.username}'은(는) 이미 사용 중인 아이디입니다."
        )

    try:
        # 2. 비밀번호 해싱 및 저장
        new_user = models.User(
            username=user.username,
            hashed_password=auth.get_password_hash(user.password)
        )
        db.add(new_user)
        db.commit()
        return {"message": "회원가입에 성공했습니다."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"서버 내부 오류: {str(e)}")

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호 틀림")
    token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/api/realtime-weather")
def get_realtime_weather(current_user: models.User = Depends(auth.get_current_user)):
    final_data = []
    for r in REALTIME_REGION_CONFIG:
        api_data = fetch_realtime_weather(r["nx"], r["ny"], r["station"])

        # API 결과가 없거나 온도 값이 없는 경우 CSV에서 보충
        if api_data is None or api_data.get("temp") is None:
            try:
                df_csv = pd.read_csv("./data/weather_data.csv")
                # 해당 지역 행 찾기
                target_row = df_csv[df_csv['region_name'] == r['name']]

                if not target_row.empty:
                    row = target_row.iloc[0]
                    # [핵심 수정] .item()을 쓰거나 float()로 감싸서 numpy 타입을 파이썬 타입으로 변환
                    api_data = {
                        "temp": float(row['ta_max']),
                        "humi": 50,
                        "pop": 10,
                        "air_status": str(row['wf_status']) if 'wf_status' in row else "보통",
                        "air_color": "#ffff00"
                    }
                else:
                    api_data = {"temp": "?", "air_status": "지역없음"}
            except Exception as e:
                print(f"CSV 로드 에러: {e}")
                api_data = {"temp": "?", "air_status": "파일에러"}

        final_data.append({**r, **api_data})

    return final_data