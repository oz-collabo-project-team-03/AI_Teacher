from typing import Union

from fastapi import APIRouter, BackgroundTasks, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.common.utils.dependency import get_current_user, get_session
from src.app.v1.user.repository.user_repository import UserRepository
from src.app.v1.user.schema.requestDto import (
    EmailRequest,
    EmailVerifyRequest,
    LoginRequest,
    StudentRegisterRequest,
    TeacherRegisterRequest,
)
from src.app.v1.user.schema.responseDto import (
    AccessTokenResponse,
    MessageResponse,
    TokenResponse,
)
from src.app.v1.user.service.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])
user_repo = UserRepository()
user_service = UserService(user_repo=user_repo)


# @router.post("/email/send", response_model=MessageResponse)
# async def send_email_verification_code(
#     payload: EmailRequest,
#     background_tasks: BackgroundTasks,
#     session: AsyncSession = Depends(get_session),
# ):
#     return await user_service.send_verification_code(
#         email=payload.email,
#         session=session,
#         background_tasks=background_tasks,
#     )
#
#
# @router.post("/email/verify", response_model=MessageResponse)
# async def verify_email_code(payload: EmailVerifyRequest):
#     return await user_service.verify_email_code(email=payload.email, code=payload.code)
#


@router.post("/register", response_model=dict)
async def register_user(
    payload: Union[StudentRegisterRequest, TeacherRegisterRequest],
    session: AsyncSession = Depends(get_session),
):
    return await user_service.register_user(payload=payload, session=session)


@router.post("/login", response_model=TokenResponse)
async def login_user(payload: LoginRequest, response: Response, session: AsyncSession = Depends(get_session)):
    return await user_service.login_user(email=payload.email, password=payload.password, response=response, session=session)


@router.post("/token/refresh", response_model=AccessTokenResponse)
async def refresh_access_token(refresh_token: str, session: AsyncSession = Depends(get_session)):
    return await user_service.refresh_access_token(refresh_token=refresh_token, session=session)


@router.post("/logout", response_model=MessageResponse)
async def logout_user(response: Response, current_user: dict = Depends(get_current_user)):
    return await user_service.logout_user(
        access_token=current_user["access_token"],
        response=response,
    )


# # @router.post("/find-email", response_model=EmailResponse)
# # async def find_email_by_phone(payload: PhoneRequest, session: AsyncSession = Depends(get_session)):
# #     return await user_service.find_email_by_phone(phone=payload.phone, session=session)
# #
# #
# # @router.post("/reset-password", response_model=MessageResponse)
# # async def reset_password(payload: EmailRequest, session: AsyncSession = Depends(get_session)):
# #     return await user_service.reset_password_service(email=payload.email, session=session)
# #
# #
# # @router.post("/verify/password", response_model=UserInfoResponse)
# # async def verify_password(
# #     payload: UpdatePasswordRequest,
# #     session: AsyncSession = Depends(get_session),
# #     current_user: dict = Depends(get_current_user),
# # ):
# #     return await user_service.update_verify_password(session=session, token=current_user["access_token"], password=payload.password)
# #
# #
# # # 유저 정보 업데이트
# # @router.put("/update/info", response_model=MessageResponse)
# # async def update_user_info(
# #     payload: UpdateUserInfoRequest,
# #     session: AsyncSession = Depends(get_session),
# #     current_user: dict = Depends(get_current_user),
# # ):
# #     return await user_service.update_user_info(session=session, token=current_user["access_token"], update_data=payload.dict())
