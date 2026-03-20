from sqlalchemy import Column, Integer, String, Float, Date
from .database import Base

class WeatherForecast(Base):
    __tablename__ = "weather_forecasts"

    id = Column(Integer, primary_key=True, index=True)
    reg_id = Column(String(10), index=True, nullable=False) # 지역 코드 (예: 11B10101 서울)
    base_date = Column(Date, nullable=False)               # 발표 날짜 (D-day)
    forecast_day = Column(Integer, nullable=False)          # 며칠 후 날짜 (3 ~ 10)

    # 3일~10일후 예보 내용 (공공데이터 API 구조에 맞춤)
    ta_min = Column(Float)  # 최저 기온
    ta_max = Column(Float)  # 최고 기온
    rn_st_am = Column(Float) # 오전 강수 확률
    rn_st_pm = Column(Float) # 오후 강수 확률
    wf_am = Column(String(50)) # 오전 날씨 (예: 맑음, 흐림)
    wf_pm = Column(String(50)) # 오후 날씨