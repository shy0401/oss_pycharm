import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# DB 파일이 저장될 data 폴더가 없다면 생성
if not os.path.exists("./data"):
    os.makedirs("./data")

# SQLite3 DB 파일 경로 설정 (data/weather.db)
SQLALCHEMY_DATABASE_URL = "sqlite:///./data/weather.db"

# DB 엔진 생성 (connect_args={"check_same_thread": False}는 SQLite 전용 필수 설정)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# DB와 통신할 세션 클래스 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# DB 모델의 베이스 클래스 (이걸 상속해서 테이블을 만듦)
Base = declarative_base()