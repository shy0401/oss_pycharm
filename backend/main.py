from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from contextlib import asynccontextmanager
from typing import Any

# 내부 모듈 임포트
from . import models, schemas, auth, database, utils
from .api.weather_client import fetch_kma_mid_term  # 명칭 확인 필요

# backend/main.py 내 REGION_CONFIG 수정
REGION_CONFIG = [
    {"name": "서울", "land": "11B00000", "ta": "11B10101", "lat": 37.5665, "lon": 126.9780},
    {"name": "대전", "land": "11C20000", "ta": "11C20401", "lat": 36.3504, "lon": 127.3845},
    {"name": "전주", "land": "11F10000", "ta": "11F20501", "lat": 35.8242, "lon": 127.1480},
    {"name": "광주", "land": "11F20000", "ta": "11F20401", "lat": 35.1595, "lon": 126.8526},
    {"name": "부산", "land": "11H20000", "ta": "11H20201", "lat": 35.1796, "lon": 129.0756},
    {"name": "울산", "land": "11H20000", "ta": "11H20101", "lat": 35.5384, "lon": 129.3114}
]

# 2. 앱 수명 주기 관리
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버 시작 시 테이블 생성 및 기초 데이터 로드
    models.Base.metadata.create_all(bind=database.engine)
    with database.get_db_context() as db: # 컨텍스트 매니저 사용 권장
        utils.load_csv_to_db(db)
    yield

app = FastAPI(
    title="Weather Info Service API",
    description="기상청 중기 예보 실시간 동기화 서비스",
    version="1.1.0",
    lifespan=lifespan
)

# 3. CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# --- 4. 인증 의존성 (Security First) ---
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증 정보가 유효하지 않거나 만료되었습니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # [하드코딩] 개발용 user0 마스터 계정 처리
    if username == "user0":
        return models.User(username="user0", id=0)

    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

# --- 5. 엔드포인트: 계정 관리 ---

@app.post("/signup", status_code=status.HTTP_201_CREATED, response_model=dict[str, str])
def signup(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    if db.query(models.User).filter(models.User.username == user.username).first():
        raise HTTPException(status_code=400, detail="이미 등록된 아이디입니다.")

    new_user = models.User(
        username=user.username,
        hashed_password=auth.get_password_hash(user.password)
    )
    db.add(new_user)
    db.commit()
    return {"message": "회원가입이 완료되었습니다."}

@app.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    # Master Account 체크
    if form_data.username == "user0" and form_data.password == "user0":
        access_token = auth.create_access_token(data={"sub": "user0"})
        return {"access_token": access_token, "token_type": "bearer"}

    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="아이디 또는 비밀번호가 일치하지 않습니다.")

    access_token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

# --- 6. 엔드포인트: 날씨 서비스 ---

@app.post("/api/sync-weather", status_code=status.HTTP_200_OK)
def sync_weather(current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    """기상청 API와 로컬 DB 데이터를 동기화합니다."""
    update_count = 0
    for r in REGION_CONFIG:
        try:
            data = fetch_kma_mid_term(r["land"], r["ta"])
            if data:
                db_record = db.query(models.MidTermForecast).filter_by(region_name=r["name"]).first()
                if db_record:
                    # 기존 데이터 업데이트
                    db_record.ta_min = data.get("ta_min")
                    db_record.ta_max = data.get("ta_max")
                    db_record.wf_status = data.get("wf")
                else:
                    # 신규 데이터 생성
                    new_record = models.MidTermForecast(
                        region_name=r["name"],
                        lat=r["lat"], lon=r["lon"],
                        land_reg_id=r["land"], ta_reg_id=r["ta"],
                        ta_min=data.get("ta_min"),
                        ta_max=data.get("ta_max"),
                        wf_status=data.get("wf")
                    )
                    db.add(new_record)
                update_count += 1
        except Exception as e:
            print(f"Failed to sync {r['name']}: {e}")
            continue

    db.commit()
    return {"message": f"{update_count}개 지역의 데이터가 동기화되었습니다."}

@app.get("/api/forecasts", response_model=dict[str, Any])
def get_forecasts(current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    """인증된 사용자에게 전체 기상 예보 데이터를 반환합니다."""
    data = db.query(models.MidTermForecast).all()
    return {
        "user": current_user.username,
        "count": len(data),
        "data": data
    }

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. 테이블 생성
    models.Base.metadata.create_all(bind=database.engine)

    # 2. CSV 데이터를 DB에 로드
    with database.get_db_context() as db:
        utils.load_csv_to_db(db)
    yield