from sqlalchemy import Column, Integer, String, Float, DateTime
from.database import Base
from datetime import datetime

class User(Base):
    """JWT 사용자 인증을 위한 데이터베이스 테이블 설계"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    # 보안 요구사항에 따라 비밀번호는 반드시 bcrypt 해시로 저장됨
    hashed_password = Column(String(255), nullable=False)

class MidTermForecast(Base):
    """기상 데이터 저장을 위한 테이블 (과거 데이터 로드용)"""
    __tablename__ = "mid_term_forecasts"

    id = Column(Integer, primary_key=True, index=True)
    region_name = Column(String(50), unique=True)
    land_reg_id = Column(String(20))
    ta_reg_id = Column(String(20))
    lat = Column(Float)
    lon = Column(Float)
    ta_min = Column(Float, nullable=True)
    ta_max = Column(Float, nullable=True)
    wf_status = Column(String(50), nullable=True)
    updated_at = Column(DateTime, default=datetime.now)