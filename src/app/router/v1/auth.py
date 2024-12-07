import logging
from typing import Union

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Header,
    HTTPException,
    Path,
    Query,
    Response,
)
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.common.utils.consts import SocialProvider, UserRole
from src.app.common.utils.dependency import get_current_user, get_session
from src.app.common.utils.image import NCPStorageService  # type: ignore

from src.app.v1.auth.repository.oauth_repository import OAuthRepository
from src.app.v1.auth.schema.requestDto import SocialLoginStudentRequest, SocialLoginTeacherRequest, OAuthRequest
from src.app.v1.auth.schema.responseDto import TeacherRoleResponse, StudentRoleResponse
from src.app.v1.auth.service.oauth_service import OAuthService
from src.app.v1.user.repository.user_repository import UserRepository
from src.app.v1.user.schema.requestDto import (
    CheckingPasswordRequest,
    EmailRequest,
    EmailVerifyRequest,
    LoginRequest,
    PhoneRequest,
    StudentRegisterRequest,
    StudyGroupRequest,
    TeacherRegisterRequest,
    UpdatePasswordRequest,
    UpdateUserInfoRequest,
)
from src.app.v1.user.schema.responseDto import (
    AccessTokenResponse,
    EmailResponse,
    MessageResponse,
    TeachersResponse,
    TempPasswordResponse,
    TokenResponse,
    UserInfoResponse,
)
from src.app.v1.user.service.user_service import UserService
from fastapi.responses import RedirectResponse


logger = logging.getLogger(__name__)


router = APIRouter(prefix="/auth", tags=["Authentication"])
user_repo = UserRepository()
user_service = UserService(user_repo=user_repo, storage_service=NCPStorageService())
oauth_repo = OAuthRepository()
oauth_service = OAuthService(oauth_repo=oauth_repo, user_repo=user_repo)


@router.post("/email/send", response_model=MessageResponse)
async def send_email_verification_code(
    payload: EmailRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    return await user_service.send_verification_code(
        email=payload.email,
        session=session,
        background_tasks=background_tasks,
    )


@router.post("/email/verify", response_model=MessageResponse)
async def verify_email_code(payload: EmailVerifyRequest):
    return await user_service.verify_email_code(email=payload.email, code=payload.code)


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
async def refresh_access_token(
    authorization: str = Header(...),  # 헤더에서 토큰 추출
    session: AsyncSession = Depends(get_session),
):
    refresh_token = authorization.replace("Bearer ", "").strip()
    return await user_service.refresh_access_token(refresh_token=refresh_token, session=session)


@router.post("/logout", response_model=MessageResponse)
async def logout_user(response: Response, current_user: dict = Depends(get_current_user)):
    return await user_service.logout_user(
        access_token=current_user["access_token"],
        response=response,
    )


@router.post("/find/email", response_model=EmailResponse)
async def find_email_by_phone(payload: PhoneRequest, session: AsyncSession = Depends(get_session)):
    return await user_service.find_email_by_phone(phone=payload.phone, session=session)


@router.post("/reset/password", response_model=TempPasswordResponse)
async def reset_password(
    payload: UpdatePasswordRequest,
    session: AsyncSession = Depends(get_session),
):
    return await user_service.reset_password(email=payload.email, session=session)


# 회원정보 변경 전 비밀번호 확인
@router.post("/verify/password", response_model=MessageResponse)
async def verify_password(
    payload: CheckingPasswordRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await user_service.checking_password(
        user_id=current_user["user_id"],
        password=payload.password,
        session=session,
    )


@router.patch("/update/info", response_model=MessageResponse)
async def update_user_info(
    payload: UpdateUserInfoRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    logger.info(f"요청 데이터: {payload.dict(exclude_unset=True)}")
    logger.info(f"현재 사용자: {current_user}")
    return await user_service.update_user_info(
        user_id=current_user["user_id"],
        role=current_user["role"],
        update_data=payload.dict(exclude_unset=True),
        session=session,
    )


# 모든 선생님 정보 조회
@router.get("/teachers", response_model=list[TeachersResponse])
async def get_all_teachers(
    session: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    logger.info(f"Current User: {current_user}")
    if current_user["role"] != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="접근 권한이 없습니다.")
    return await user_service.get_all_teachers_info(session)


# 최초 로그인 시 선생님 선택 -> 스터디 그룹 형성
@router.post("/groups/study", response_model=MessageResponse)
async def create_study_group(
    study_group: StudyGroupRequest,
    session: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    return await user_service.create_study_group(
        session=session,
        current_user=current_user,
        teacher_id=study_group.teacher_id,
        teacher_name=study_group.name,
    )

# 로그인 엔드포인트 - 테스트
# @router.get("/login/{provider}")
# async def login(provider: str):
#     oauth_url = oauth_service.get_oauth_url(provider)
#     print(f"Generated OAuth URL: {oauth_url}")
#     return RedirectResponse(oauth_url)

# Callback 엔드포인트
@router.post("/login/callback/{provider}")
async def social_login_callback(
        response: Response,
        body: OAuthRequest,
        provider: str = Path(...),
        session: AsyncSession = Depends(get_session),
):
    code = body.code

    token_data = await oauth_service.get_access_token(provider, code)
    access_token = token_data.get("access_token")
    user_info = await oauth_service.get_user_info(provider, access_token)
    saved_user = await oauth_service.save_user_info(provider, user_info, session)
    result = await oauth_service.login_social_user(saved_user, response)

    return result

@router.patch("/social/info/student", response_model=StudentRoleResponse)
async def additional_student_info(
    payload: SocialLoginStudentRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    user_id = current_user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="유효하지 않은 사용자입니다.")

    return await oauth_service.update_student_info(payload=payload, user_id=user_id, session=session)


@router.patch("/social/info/teacher", response_model=TeacherRoleResponse)
async def additional_teacher_info(
    payload: SocialLoginTeacherRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    user_id = current_user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="유효하지 않은 사용자입니다.")

    return await oauth_service.update_teacher_info(payload=payload, user_id=user_id, session=session)
