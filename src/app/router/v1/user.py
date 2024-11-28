from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.common.utils.dependency import get_session
from src.app.v1.user.repository.user_repository import UserRepository
from src.app.v1.user.schema.responseDto import ProfileResponse
from src.app.v1.user.service.user_service import UserService

router = APIRouter(prefix="/user", tags=["Mypage"])
user_repo = UserRepository()
user_service = UserService(user_repo=user_repo)


# 다른 사람이 유저 조회
# @router.get("/profile/{user_id}", response_model=ProfileResponse)
# async def get_user_profile(user_id: int, session: AsyncSession = Depends(get_session)):
#     return await user_service.get_user_profile(session, user_id)
