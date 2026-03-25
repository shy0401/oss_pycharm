# backend/models.py

from sqlalchemy import Column, Integer, String, Float, DateTime  # <-- DateTime 추가!
from .database import Base
from datetime import datetime  # <-- default=datetime.now를 위해 추가!

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)

class MidTermForecast(Base):
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

    # 여기서 DateTime과 datetime.now가 사용됩니다.
    updated_at = Column(DateTime, default=datetime.now)