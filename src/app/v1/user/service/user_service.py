import logging
import os
import random
import re
import string
import uuid
from datetime import datetime, timedelta
from typing import Union
from urllib.parse import unquote

import jwt
from fastapi import BackgroundTasks, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.common.utils.consts import GradeNumber, UserRole
from src.app.common.utils.redis import (
    delete_from_redis,
    get_from_redis,
    get_redis_key_jti,
    get_redis_key_refresh_token,
    save_to_redis,
)
from src.app.common.utils.security import (
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    create_refresh_token,
    verify_access_token,
)
from src.app.common.utils.send_email import send_email
from src.app.common.utils.verify_password import (
    hash_password,
    validate_password_complexity,
    verify_password,
)
from src.app.v1.user.entity.user import User
from src.app.v1.user.repository.user_repository import UserRepository
from src.app.v1.user.schema.requestDto import (
    StudentRegisterRequest,
    TeacherRegisterRequest,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

EMAIL_VERIFICATION_EXPIRY = 180  # 3분
SECURE_COOKIE = os.getenv("SECURE_COOKIE", "false").lower() == "true"
EMAIL_VERIFICATION_KEY_TEMPLATE = "verification:email:{email}"


class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    @staticmethod
    def _validate_email_format(email: str) -> bool:
        email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(email_regex, email))

    @staticmethod
    def _generate_verification_code(length: int = 6) -> str:
        return "".join(random.choices("0123456789", k=length))

    async def send_verification_code(self, email: str, session: AsyncSession, background_tasks: BackgroundTasks) -> dict:

        if not self._validate_email_format(email):
            raise HTTPException(status_code=400, detail="유효한 이메일 형식이 아닙니다.")

        existing_user = await self.user_repo.get_user_by_email(session, email)
        if existing_user:
            raise HTTPException(status_code=400, detail="이미 등록된 이메일입니다.")

        redis_key = EMAIL_VERIFICATION_KEY_TEMPLATE.format(email=email)
        existing_code = await get_from_redis(redis_key)
        if existing_code:
            raise HTTPException(status_code=400, detail="이미 인증 코드가 발송되었습니다. 남은 인증 시간 이후에 시도해 주세요.")

        verification_code = self._generate_verification_code()
        await save_to_redis(redis_key, verification_code, EMAIL_VERIFICATION_EXPIRY)

        background_tasks.add_task(
            send_email, recipient=email, subject="이메일 인증 코드", body=f"인증 코드: {verification_code}\n3분 안에 입력해 주세요."
        )

        return {"message": f"인증 코드가 {email}로 전송되었습니다. 3분 안에 입력해 주세요."}

    async def verify_email_code(self, email: str, code: str) -> dict:
        redis_key = EMAIL_VERIFICATION_KEY_TEMPLATE.format(email=email)
        stored_code = await get_from_redis(redis_key)

        if not stored_code:
            raise HTTPException(status_code=400, detail="인증 코드가 만료되었거나 잘못된 요청입니다.")
        if stored_code != code:
            raise HTTPException(status_code=400, detail="인증 코드가 일치하지 않습니다.")

        await delete_from_redis(redis_key)

        return {"message": "이메일 인증에 성공하였습니다."}

    async def register_user(self, payload: Union[StudentRegisterRequest, TeacherRegisterRequest], session: AsyncSession):
        logger.info(f"Registering user with payload: {payload}")

        try:
            if payload.password != payload.password_confirm:
                raise HTTPException(status_code=400, detail="비밀번호 확인이 일치하지 않습니다.")
            if not validate_password_complexity(payload.password):
                raise HTTPException(status_code=400, detail="비밀번호는 10~20자의 영문, 숫자, 특수문자가 포함되어야 합니다.")

            hashed_password = hash_password(payload.password)

            # 유저 데이터 준비 및 생성
            if isinstance(payload, StudentRegisterRequest):
                user_data = self._prepare_student_data(payload, hashed_password)
                await self.user_repo.create_student(session, user_data, user_data["student_data"])
            elif isinstance(payload, TeacherRegisterRequest):
                user_data = self._prepare_teacher_data(payload, hashed_password)
                await self.user_repo.create_teacher(session, user_data, user_data["teacher_data"])
            else:
                raise HTTPException(status_code=400, detail="유효하지 않은 역할입니다.")

            return {"message": "회원가입이 완료되었습니다."}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error during user registration: {e}")
            raise HTTPException(status_code=500, detail="회원가입 중 오류가 발생했습니다.")

    def _prepare_student_data(self, payload: StudentRegisterRequest, hashed_password: str):
        return {
            "email": payload.email,
            "password": hashed_password,
            "phone": payload.phone,
            "is_privacy_accepted": payload.is_privacy_accepted,
            "role": UserRole.STUDENT,
            "student_data": {
                "school": payload.school,
                "grade": payload.grade,
                "career_aspiration": payload.career_aspiration,
                "interest": payload.interests,
            },
            "nickname": payload.nickname,
        }

    def _prepare_teacher_data(self, payload: TeacherRegisterRequest, hashed_password: str):
        return {
            "email": payload.email,
            "password": hashed_password,
            "phone": payload.phone,
            "is_privacy_accepted": payload.is_privacy_accepted,
            "role": UserRole.TEACHER,
            "teacher_data": {
                "organization_name": payload.organization_name,
                "organization_type": payload.organization_type,
                "position": payload.position,
            },
            "nickname": payload.nickname,
        }

    async def login_user(self, email: str, password: str, response: Response, session: AsyncSession):
        user = await self.user_repo.get_user_by_email(session, email)
        if user is None:
            raise HTTPException(status_code=404, detail="등록되지 않은 이메일입니다.")

        if not verify_password(password, user.password):
            raise HTTPException(status_code=401, detail="비밀번호가 틀렸습니다.")

        role = str(user.role) if not isinstance(user.role, str) else user.role

        jti = str(uuid.uuid4())
        access_token = create_access_token(
            {"sub": str(user.id), "role": role, "jti": jti}, expires_delta=timedelta(minutes=15)  # 문자열로 변환된 role 사용
        )
        refresh_token = create_refresh_token({"sub": str(user.id)}, expires_delta=timedelta(days=7))

        expiry = 15 * 60
        await save_to_redis(get_redis_key_jti(jti), "used", expiry)
        await save_to_redis(get_redis_key_refresh_token(user.id), refresh_token, expiry=7 * 24 * 3600)

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,  # 클라이언트 측 JavaScript에서 쿠키에 접근하지 못하도록 제한 ->XSS공격으로부터 보호하기 위해
            secure=SECURE_COOKIE,  # 배포 시에는 True 로 전환 ->  HTTPS 연결에서만 쿠키를 전송하도록 제한
            samesite="Strict",  # type: ignore # CSRF(Cross-Site Request Forgery) 공격을 방지
            max_age=7 * 24 * 3600,
        )
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": 900,
            "message": "로그인에 성공하였습니다.",
        }

    async def refresh_access_token(self, refresh_token: str, session: AsyncSession):
        if not refresh_token:
            raise HTTPException(status_code=401, detail="Refresh Token이 제공되지 않았습니다.")

        try:
            payload = verify_access_token(refresh_token)
            user_id = int(payload.get("sub"))
            if not user_id:
                raise HTTPException(status_code=401, detail="Refresh Token 정보가 유효하지 않습니다.")

            user = await self.user_repo.get_user_by_id(session, user_id)
            if not user:
                raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

            redis_key = get_redis_key_refresh_token(user_id)
            stored_refresh_token = await get_from_redis(redis_key)

            if not stored_refresh_token:
                raise HTTPException(status_code=401, detail="Refresh Token이 만료되었거나 존재하지 않습니다.")

            if stored_refresh_token.strip() != refresh_token.strip():
                raise HTTPException(status_code=401, detail="Refresh Token이 일치하지 않습니다.")

            role = str(user.role) if not isinstance(user.role, str) else user.role
            jti = str(uuid.uuid4())
            access_token = create_access_token(
                {"sub": str(user.id), "role": role, "jti": jti},
                expires_delta=timedelta(minutes=15),
            )

            expiry = 15 * 60
            jti_key = get_redis_key_jti(jti)
            await save_to_redis(jti_key, "used", expiry)

            return {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": expiry,
                "message": "access token이 성공적으로 발급되었습니다.",
            }

        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Refresh Token이 만료되었습니다.")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="유효하지 않은 Refresh Token입니다.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

    async def logout_user(self, access_token: str, response: Response):
        try:
            payload = verify_access_token(access_token)
            jti = payload.get("jti")
            expiry = payload.get("exp") - int(datetime.now().timestamp())

            user_id = payload.get("sub")
            if user_id:
                await delete_from_redis(get_redis_key_refresh_token(user_id))

            response.delete_cookie(key="refresh_token")
            return {"message": "로그아웃이 완료되었습니다."}
        except jwt.ExpiredSignatureError:

            user_id = None
            try:
                payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
                user_id = payload.get("sub")
            except Exception:
                pass
            if user_id:
                await delete_from_redis(get_redis_key_refresh_token(user_id))
                response.delete_cookie(key="refresh_token")
            raise HTTPException(status_code=401, detail="Access Token이 만료되었습니다.")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="유효하지 않은 Access Token입니다.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"로그아웃 중 서버 오류가 발생했습니다: {str(e)}")

    async def find_email_by_phone(self, phone: str, session: AsyncSession) -> dict:
        if not phone:
            raise HTTPException(status_code=400, detail="핸드폰 번호를 입력해 주세요.")

        query = select(User).where(User.phone == phone)
        result = await session.execute(query)
        user = result.scalars().first()

        if not user:
            raise HTTPException(status_code=404, detail="해당 번호로 등록된 유저를 찾을 수 없습니다.")

        email = user.email
        masked_email = self._mask_email(email)  # 이메일 마스킹 처리
        return {"email": masked_email}

    def _mask_email(self, email: str) -> str:
        try:
            local_part, domain_part = email.split("@")
            masked_local = local_part[0] + "***"
            return f"{masked_local}@{domain_part}"
        except Exception:
            raise HTTPException(status_code=400, detail="잘못된 이메일 형식입니다.")

    async def reset_password_service(self, email: str, session: AsyncSession) -> dict:
        query = select(User).where(User.email == email)
        result = await session.execute(query)
        user = result.scalars().first()

        if not user:
            raise HTTPException(status_code=404, detail="등록되지 않은 이메일입니다.")

        temp_password = self._generate_temp_password()
        hashed_password = hash_password(temp_password)

        user.password = hashed_password
        try:
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise HTTPException(status_code=500, detail=f"임시 비밀번호 저장 실패: {str(e)}")

        return {"message": "임시 비밀번호가 발급되었습니다.", "temp_password": temp_password}

    def _generate_temp_password(self, length: int = 12) -> str:
        if length < 10 or length > 20:
            raise ValueError("비밀번호 길이는 10~20자 사이여야 합니다.")
        characters = string.ascii_letters + string.digits
        return "".join(random.choices(characters, k=length))

    async def update_verify_password(self, session: AsyncSession, token: str, password: str) -> dict:

        token_payload = verify_access_token(token)
        user_id = int(token_payload.get("sub"))

        user = await self.user_repo.get_user_by_id(session, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="유저를 찾을 수 없습니다.")

        if not verify_password(password, user.password):
            raise HTTPException(status_code=401, detail="비밀번호가 일치하지 않습니다.")

        user_info = {
            "email": user.email,
            "phone": user.phone,
        }

        if user.role == UserRole.STUDENT:
            user_info.update(
                {
                    "school": user.student.school,
                    "grade": user.student.grade.name,
                }
            )

        return user_info

    async def update_user_info(self, session: AsyncSession, token: str, update_data: dict) -> dict:
        token_payload = verify_access_token(token)
        user_id = int(token_payload.get("sub"))
        role = token_payload.get("role")

        updatable_fields = self._get_updatable_fields(role)
        self._validate_update_fields(update_data, updatable_fields)

        update_dict = await self._prepare_update_data(session, update_data)

        try:
            await self.user_repo.update_user(session, user_id, update_dict)
            return {"message": "성공적으로 업데이트되었습니다."}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating user info: {e}")
            raise HTTPException(status_code=500, detail="사용자 정보 업데이트 중 오류가 발생했습니다.")

    def _get_updatable_fields(self, role):
        if role == UserRole.TEACHER:
            return {"email", "password", "phone"}
        elif role == UserRole.STUDENT:
            return {"email", "password", "phone", "school", "grade"}
        else:
            raise HTTPException(status_code=400, detail="유효하지 않은 사용자 역할입니다.")

    def _validate_update_fields(self, update_data, updatable_fields):
        invalid_fields = set(update_data.keys()) - updatable_fields
        if invalid_fields:
            raise HTTPException(status_code=400, detail=f"{', '.join(invalid_fields)}는 변경할 수 없는 필드입니다.")

    async def _prepare_update_data(self, session, update_data):
        update_dict = {}
        for field, value in update_data.items():
            if field == "email":
                await self._validate_email(session, value)
                update_dict["email"] = value
            elif field == "password":
                self._validate_password(value, update_data.get("password_confirm"))
                update_dict["password"] = hash_password(value)
            elif field in {"phone", "school"}:
                update_dict[field] = value
            elif field == "grade":
                update_dict["grade"] = GradeNumber(value)
        return update_dict

    async def _validate_email(self, session, email):
        if not self._validate_email_format(email):
            raise HTTPException(status_code=400, detail="유효한 이메일 형식이 아닙니다.")
        existing_email_user = await self.user_repo.get_user_by_email(session, email)
        if existing_email_user:
            raise HTTPException(status_code=400, detail="이미 사용 중인 이메일입니다.")
