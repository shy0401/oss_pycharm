import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt, JWTError
from passlib.context import CryptContext
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 환경 변수에서 가져오되, 없을 경우에 대한 방어 로직 추가
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    # 개발 환경에서 키가 없을 경우를 대비한 임시 키 (실 운영시 반드시 .env 설정 필요)
    SECRET_KEY = "dev-secret-key-at-least-32-chars-long!!"

ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

# Bcrypt 해싱 설정
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """평문 비밀번호와 해싱된 비밀번호를 비교합니다."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    # bcrypt는 72바이트까지만 지원하므로 초과 시 잘라내거나 에러 처리
    if len(password.encode('utf-8')) > 72:
        password = password[:72]
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    JWT 액세스 토큰을 생성합니다.
    - datetime.utcnow() 대신 timezone-aware한 datetime.now(timezone.utc)를 사용합니다.
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt