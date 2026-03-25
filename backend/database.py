import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

# 1. 환경 변수 로드 (.env 파일에 DATABASE_URL 등이 있을 경우 우선 사용)
load_dotenv()

# 2. 프로젝트 경로 및 DB 저장 폴더 자동 설정
# 현재 파일(backend/database.py) 위치 기준으로 프로젝트 루트를 찾습니다.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(BASE_DIR, "data")

# data 폴더가 없으면 자동으로 생성하여 FileNotFoundError 방지
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

# SQLite DB 파일 경로 설정 (기본값: ./data/weather.db)
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{os.path.join(DB_DIR, 'weather.db')}"
)

# 3. SQLAlchemy 엔진 생성
# SQLite 사용 시 'check_same_thread=False'는 멀티스레드 환경(FastAPI)에서 필수 설정입니다.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
)

# 4. 세션 설정 (SessionLocal)
# autocommit=False: 명시적으로 db.commit()을 호출할 때만 저장하여 데이터 안정성 확보
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 5. 모델 생성을 위한 기본 클래스
Base = declarative_base()

# 6. [FastAPI용] 의존성 주입(Dependency Injection) 함수
def get_db():
    """
    FastAPI 경로 함수(Endpoints)에서 Depends(get_db)로 호출할 때 사용합니다.
    요청이 들어올 때 세션을 열고, 응답이 나가면 자동으로 닫아줍니다.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 7. [일반 스크립트용] 컨텍스트 매니저
@contextmanager
def get_db_context():
    """
    FastAPI 외부(예: lifespan 초기화, utils.py 데이터 적재)에서
    'with get_db_context() as db:' 형태로 사용합니다.
    에러 발생 시 자동으로 롤백(Rollback)을 수행하여 DB 무결성을 유지합니다.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()  # 성공적으로 블록이 끝나면 자동 커밋
    except Exception as e:
        db.rollback()  # 에러 발생 시 변경 사항 취소
        raise e
    finally:
        db.close()  # 작업 완료 후 세션 반환