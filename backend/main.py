from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
from typing import List, Dict, Any

# 내부 모듈 임포트
from . import models, schemas, auth, database, utils
from .api.weather_client import fetch_realtime_weather

# 주요 도시별 격자 좌표(NX, NY) 및 미세먼지 측정소 설정
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
    # 서버 시작 시 테이블 생성
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

# --- 인증 관련 엔드포인트 ---

@app.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="이미 존재하는 아이디입니다.")
    new_user = models.User(username=user.username, hashed_password=auth.get_password_hash(user.password))
    db.add(new_user)
    db.commit()
    return {"message": "가입 성공"}

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호 틀림")
    token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}

# --- 실시간 날씨 데이터 엔드포인트 ---

@app.get("/api/realtime-weather", response_model=List[Dict[str, Any]])
def get_realtime_weather(current_user: models.User = Depends(auth.get_current_user)):
    """API로부터 실시간 데이터를 직접 가져와 반환 (DB 거치지 않음)"""
    final_data = []
    for r in REALTIME_REGION_CONFIG:
        api_data = fetch_realtime_weather(r["nx"], r["ny"], r["station"])
        region_result = {**r, **(api_data if api_data else {})}
        final_data.append(region_result)
    return final_data