from pydantic import BaseModel

class UserCreate(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    username: str
    class Config:
        from_attributes = True  # ORM 객체를 Pydantic 모델로 변환 허용

class Token(BaseModel):
    access_token: str
    token_type: str