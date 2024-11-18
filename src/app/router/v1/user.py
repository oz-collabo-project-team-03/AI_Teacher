from fastapi import APIRouter, BackgroundTasks, Header, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.v1.user.schema.requestDto import (
    EmailSendRequest,
    EmailVerifyRequest,
    LoginRequest,
    RegisterRequest,
)
from src.app.v1.user.schema.responseDto import EmailResponse, TokenResponse
from src.app.v1.user.service.user_service import (
    find_email_by_phone_service,
    login_user_service,
    logout_user_service,
    refresh_access_token_service,
    register_user_service,
    reset_password_service,
    send_verification_email_service,
    verify_email_code_service,
)
router = APIRouter(prefix="/auth", tags=["Authentication"])
# 이메일 인증 코드 보내기
@router.post("/email/send", response_model=EmailResponse)
async def send_verification_email(
    payload: EmailSendRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession,
):
    return await send_verification_email_service(payload.email, background_tasks, session)


# 이메일 인증 코드 확인
@router.post("/email/verify", response_model=EmailResponse)
async def verify_email_code(payload: EmailVerifyRequest):
    return await verify_email_code_service(payload.email, payload.code)


# 회원 가입
@router.post("/register", response_model=TokenResponse)
async def register_user(
    payload: RegisterRequest,
    response: Response,
    session: AsyncSession,
):
    return await register_user_service(payload, session, response)


@router.post("/login", response_model=TokenResponse)
async def login_user(
    payload: LoginRequest,
    response: Response,
    session: AsyncSession,
):
    return await login_user_service(payload.email, payload.password, response, session)


@router.post("/token/refresh")
async def refresh_access_token(request: Request):
    refresh_token = request.cookies.get("refresh_token")
    return await refresh_access_token_service(refresh_token or "")


@router.post("/logout")
async def logout_user(
    authorization: str = Header(None),
    request=Request,
    response=Response,
    session=AsyncSession,
):
    refresh_token = request.cookies.get("refresh_token")
    return await logout_user_service(authorization, refresh_token, response)


@router.post("/find-email")
async def find_email_by_phone(phone: str, session: AsyncSession):
    return await find_email_by_phone_service(phone, session)


@router.post("/reset-password")
async def reset_password(email: str, session: AsyncSession):
    return await reset_password_service(email, session)
