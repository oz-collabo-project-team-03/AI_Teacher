import enum
import json
import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from fastapi import HTTPException, status
from jose import jwt  # type: ignore

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"


def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=15)):
    def custom_serializer(obj):
        if isinstance(obj, enum.Enum):
            return obj.value
        if hasattr(obj, "__str__"):
            return str(obj)
        raise TypeError(f"Type {type(obj)} is not JSON serializable")

    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
        to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(json.loads(json.dumps(to_encode, default=custom_serializer)), SECRET_KEY, algorithm=ALGORITHM)  # 사용자 정의 직렬화 적용
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: timedelta = timedelta(days=7)):
    to_encode = data.copy()
    expire = datetime.now() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Access Token이 만료되었습니다.")
    except jwt.JWTError:  # type: ignore
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="유효하지 않은 Access Token입니다.")
