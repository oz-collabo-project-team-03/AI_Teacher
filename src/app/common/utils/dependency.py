from typing import AsyncGenerator, TypedDict

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.common.utils.security import verify_access_token
from src.config.database.postgresql import SessionLocal

# OAuth2 스키마 정의
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


# DB 세션 의존성
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    try:
        async with SessionLocal() as session:
            yield session
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


class CurrentUser(TypedDict):
    user_id: str
    role: str
    auth_provider: str
    access_token: str


async def get_current_user(token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = verify_access_token(token)
    return {"access_token": token, "user_id": payload.get("sub"), "role": payload.get("role")}
