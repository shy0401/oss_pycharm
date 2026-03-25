import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

# 1. 환경 변수 로드
load_dotenv()

# 2. DB 경로 및 URL 설정
# 프로젝트 루트의 data 폴더에 저장되도록 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(BASE_DIR, "data")
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(DB_DIR, 'weather.db')}")

# 3. 엔진 생성
# SQLite는 한 번에 하나의 스레드만 허용하므로, FastAPI의 멀티스레딩 환경을 위해
# check_same_thread=False 옵션이 필수입니다.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
)

# 4. 세션 팩토리 설정
# autocommit/autoflush를 False로 두어 데이터 무결성을 직접 제어합니다.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 5. 모델 베이스 클래스
Base = declarative_base()

# 6. [FastAPI 전용] 의존성 주입 함수
def get_db():
    """
    FastAPI의 Depends(get_db)를 통해 안전하게 세션을 획득하고
    응답이 끝나면 자동으로 세션을 닫습니다.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 7. [범용] 컨텍스트 매니저 (추가 권장)
@contextmanager
def get_db_context():
    """
    FastAPI 외부(예: utils.py, migration script)에서
    'with get_db_context() as db:' 형태로 안전하게 사용할 때 사용합니다.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit() # 성공 시 자동 커밋
    except Exception:
        db.rollback() # 에러 시 롤백
        raise
    finally:
        db.close()