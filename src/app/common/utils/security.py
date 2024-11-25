import json
import logging
import os
import uuid
from datetime import datetime, timedelta

import jwt
from dotenv import load_dotenv
from fastapi import HTTPException, status

# 로그 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key")
ALGORITHM = "HS256"


def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=15)):
    to_encode = data.copy()
    expire = datetime.now() + expires_delta
    to_encode.update({"exp": int(expire.timestamp()), "jti": str(uuid.uuid4())})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict, expires_delta: timedelta = timedelta(days=7)):
    to_encode = data.copy()
    expire = datetime.now() + expires_delta
    to_encode.update({"exp": int(expire.timestamp()), "jti": str(uuid.uuid4())})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str, verify_exp: bool = True) -> dict:
    try:
        logger.info(f"디코딩할 토큰: {token}")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": verify_exp})
        logger.info(f"디코딩된 페이로드: {payload}")
        return payload
    except jwt.ExpiredSignatureError:
        logger.error("JWT가 만료되었습니다.")
        raise HTTPException(status_code=401, detail="JWT가 만료되었습니다.")
    except jwt.DecodeError as e:
        logger.error(f"JWT 디코드 오류: {e}")
        raise HTTPException(status_code=400, detail=f"JWT 디코드 오류: {str(e)}")
    except Exception as e:
        logger.error(f"JWT 디코드 중 알 수 없는 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=f"JWT 디코드 중 알 수 없는 오류 발생: {str(e)}")


def verify_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp_timestamp = payload.get("exp")
        if exp_timestamp:
            exp_time = datetime.fromtimestamp(exp_timestamp)
            if exp_time < datetime.now():
                raise HTTPException(status_code=401, detail="Access Token이 만료되었습니다.")

        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Access Token이 만료되었습니다.")
    except jwt.DecodeError as e:
        raise HTTPException(status_code=400, detail=f"JWT 디코드 오류: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Access Token 검증 중 오류가 발생했습니다: {str(e)}")
