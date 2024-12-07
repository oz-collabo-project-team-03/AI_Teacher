from typing import Union

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.common.utils.dependency import get_current_user, get_session
from src.app.common.utils.image import NCPStorageService  # type: ignore
from src.app.v1.auth.schema.responseDto import MessageResponse
from src.app.v1.user.repository.user_repository import UserRepository
from src.app.v1.user.schema.requestDto import (
    UpdateStudentProfileRequest,
    UpdateTeacherProfileRequest,
)
from src.app.v1.user.schema.responseDto import (
    StudentProfileResponse,
    TeacherProfileResponse,
)
from src.app.v1.user.service.user_service import UserService

router = APIRouter(prefix="/users", tags=["Mypage"])
user_repo = UserRepository()
storage_service = NCPStorageService()
user_service = UserService(user_repo, storage_service)


# 자신 -> 내 프로필 조회
@router.get("/profile/me", response_model=Union[StudentProfileResponse, TeacherProfileResponse])
async def get_profile(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    print(f"current_user['role']: {current_user['role']}")
    return await user_service.get_my_profile(
        user_id=current_user["user_id"],
        role=current_user["role"],
        session=session,
    )


# 타인 -> 내 프로필 조회
@router.get("/profile/{user_id}", response_model=Union[StudentProfileResponse, TeacherProfileResponse])
async def get_user_profile(
    user_id: int,
    session: AsyncSession = Depends(get_session),
):
    return await user_service.get_user_profile_by_id(
        user_id=user_id,
        session=session,
    )


# 학생 프로필 변경
@router.patch("/profile/student", response_model=MessageResponse)
async def update_student_profile(
    request: UpdateStudentProfileRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await user_service.update_student_profile(
        user_id=current_user["user_id"],
        update_data=request.dict(exclude_unset=True),
        session=session,
    )


@router.patch("/profile/teacher", response_model=MessageResponse)
async def update_teacher_profile(
    request: UpdateTeacherProfileRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await user_service.update_teacher_profile(
        user_id=current_user["user_id"],
        update_data=request.dict(exclude_unset=True),
        session=session,
    )


@router.post("/deactivate", response_model=MessageResponse)
async def deactivate_user(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await user_service.deactivate_user_service(user_id=current_user["user_id"], session=session)
