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


async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        logger.info("Extracting user information from Access Token.")
        if not token:
            logger.warning("Access Token is missing.")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Access Token이 제공되지 않았습니다.")

        payload = verify_access_token(token)
        logger.info(f"User authenticated: {payload}")
        return {
            "access_token": token,
            "user_id": payload.get("sub"),
            "role": payload.get("role"),
        }
    except HTTPException as e:
        logger.error(f"Authentication failed: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during user authentication: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"사용자 인증 중 서버 오류가 발생했습니다: {str(e)}")
