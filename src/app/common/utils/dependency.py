import logging
from typing import AsyncGenerator, TypedDict

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.common.utils.security import verify_access_token
from src.config.database.postgresql import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OAuth2 스키마 정의
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# DB 세션 의존성
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    try:
        async with SessionLocal() as session:
            yield session
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
):

    try:
        logger.info("Starting authentication process...")
        if not token:
            logger.warning("Access Token is missing.")
            raise HTTPException(status_code=401, detail="Access Token이 제공되지 않았습니다.")

        logger.info(f"Access Token received: {token}")

        payload = verify_access_token(token)
        logger.info(f"Decoded payload: {payload}")

        user_id = payload.get("sub")
        role = payload.get("role")

        if not user_id or not role:
            logger.warning(f"Invalid token payload: {payload}")
            raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")

        logger.info(f"User authenticated successfully: user_id={user_id}, role={role}")
        return {
            "access_token": token,
            "user_id": int(user_id),
            "role": role,
        }

    except HTTPException as e:
        logger.error(f"Authentication failed with HTTPException: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during user authentication: {str(e)}")
        raise HTTPException(status_code=500, detail=f"사용자 인증 중 서버 오류가 발생했습니다: {str(e)}")
