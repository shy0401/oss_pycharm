from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from .database import SessionLocal, engine
from . import models

# 서버 시작 시 SQLite 테이블이 없다면 자동으로 생성
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Weather Map Backend")

# DB 세션을 가져오고 자동으로 닫아주는 유틸리티 함수
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"message": "Weather Backend API is running!"}

# 나중에 Streamlit이 호출할 API 예시 (지역별 최신 예보 가져오기)
@app.get("/api/forecast/{reg_id}")
def get_forecast_by_region(reg_id: str, db: Session = Depends(get_db)):
    forecast = db.query(models.WeatherForecast) \
        .filter(models.WeatherForecast.reg_id == reg_id) \
        .first()
    if not forecast:
        return {"status": "success", "data": None, "message": f"No data found for region: {reg_id}"}
    return {"status": "success", "data": forecast}