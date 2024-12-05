import logging
import os
import random
import re
import string
import uuid
from datetime import datetime, timedelta
from typing import Union

import jwt
from email_validator import EmailNotValidError, validate_email
from fastapi import BackgroundTasks, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.common.models.tag import Tag
from src.app.common.utils.consts import UserRole
from src.app.common.utils.image import NCPStorageService  # type: ignore
from src.app.common.utils.redis_utils import (
    REFRESH_TOKEN_TTL,
    delete_from_redis,
    get_from_redis,
    get_redis_key_jti,
    get_redis_key_refresh_token,
    mark_jti_used,
    save_to_redis,
)
from src.app.common.utils.security import (
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    create_refresh_token,
    verify_access_token,
)
from src.app.common.utils.send_email import send_email_async
from src.app.common.utils.verify_password import (
    generate_temp_password,
    hash_password,
    validate_password_complexity,
    validate_temp_password_complexity,
    verify_password,
)
from src.app.v1.user.entity.organization import Organization
from src.app.v1.user.entity.student import Student
from src.app.v1.user.entity.teacher import Teacher
from src.app.v1.user.entity.user import User
from src.app.v1.user.repository.user_repository import UserRepository
from src.app.v1.user.schema.requestDto import (
    BaseRegisterRequest,
    StudentRegisterRequest,
    TeacherRegisterRequest,
)
from src.app.v1.user.schema.responseDto import (
    CommonProfileResponse,
    PostResponse,
    StudentProfileResponse,
    TeacherProfileResponse,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

EMAIL_VERIFICATION_EXPIRY = 180  # 3분
SECURE_COOKIE = os.getenv("SECURE_COOKIE", "false").lower() == "true"
EMAIL_VERIFICATION_KEY_TEMPLATE = "verification:email:{email}"


class UserService:
    def __init__(self, user_repo: UserRepository, storage_service: NCPStorageService):
        self.user_repo = user_repo
        self.storage_service = storage_service

    @staticmethod
    def _validate_email_format(email: str) -> bool:
        try:
            validate_email(email)
            return True
        except EmailNotValidError as e:
            logger.warning(f"유효하지 않은 이메일 형식: {email} - {e}")
            return False

    # 랜덤 6자리 숫자
    @staticmethod
    def _generate_verification_code(length: int = 6) -> str:
        return "".join(random.choices("0123456789", k=length))

    # 인증 코드 발송
    async def send_verification_code(self, email: str, session: AsyncSession, background_tasks: BackgroundTasks) -> dict:

        if not self._validate_email_format(email):
            raise HTTPException(status_code=400, detail="유효한 이메일 형식이 아닙니다.")

        # 인증 코드 생성
        verification_code = self._generate_verification_code()
        redis_key = EMAIL_VERIFICATION_KEY_TEMPLATE.format(email=email)

        logger.info(f"Redis 저장 시도: Key={redis_key}, Value={verification_code}, Expiry={EMAIL_VERIFICATION_EXPIRY}")

        # Redis에 저장
        try:
            await save_to_redis(redis_key, verification_code, EMAIL_VERIFICATION_EXPIRY)
            logger.info(f"Redis 저장 성공: Key={redis_key}")
        except Exception as e:
            logger.error(f"Redis 저장 실패: {e}")
            raise HTTPException(status_code=500, detail="Redis 저장 중 문제가 발생했습니다.")

        # 이메일 발송 (비동기로 처리)
        subject = "이메일 인증 코드"
        body = f"인증코드:{verification_code}\n3분 안에 입력해 주세요."

        background_tasks.add_task(
            send_email_async,
            recipient=email,
            subject=subject,
            body=body,
        )

        return {"message": f"인증 코드가 {email}로 전송되었습니다. 3분 안에 입력해 주세요."}

    async def verify_email_code(self, email: str, code: str) -> dict:
        redis_key = EMAIL_VERIFICATION_KEY_TEMPLATE.format(email=email)

        # Redis에서 인증 코드 조회
        try:
            stored_code = await get_from_redis(redis_key)
            logger.info(f"Redis 조회 성공: Key={redis_key}, Value={stored_code}")
        except Exception as e:
            logger.error(f"Redis 조회 오류: {e}")
            raise HTTPException(status_code=500, detail="Redis에서 인증 코드를 확인하는 중 문제가 발생했습니다.")

        if not stored_code:
            logger.warning(f"인증 코드 만료 또는 존재하지 않음: Key={redis_key}")
            raise HTTPException(status_code=400, detail="인증 코드가 만료되었거나 존재하지 않습니다.")

        if stored_code != code:
            logger.warning(f"인증 코드 불일치: 입력={code}, 저장={stored_code}")
            raise HTTPException(status_code=400, detail="인증 코드가 일치하지 않습니다.")

        # Redis에서 인증 코드 삭제
        try:
            await delete_from_redis(redis_key)
            logger.info(f"Redis 삭제 성공: Key={redis_key}")
        except Exception as e:
            logger.error(f"Redis 삭제 오류: {e}")
            raise HTTPException(status_code=500, detail="Redis에서 인증 코드 삭제 중 문제가 발생했습니다.")

        return {"message": "이메일 인증이 완료되었습니다."}

    async def register_user(self, payload: Union[StudentRegisterRequest, TeacherRegisterRequest], session: AsyncSession):
        try:
            if payload.password != payload.password_confirm:
                raise HTTPException(status_code=400, detail="비밀번호 확인이 일치하지 않습니다.")

            validation_result = validate_password_complexity(payload.password)

            if not validation_result:
                raise HTTPException(status_code=400, detail="비밀번호는 영문(대소, 숫자, 특수문자 10~20자 이내 여야 합니다.")

            hashed_password = hash_password(payload.password)

            if payload.role == UserRole.STUDENT:
                student_payload = StudentRegisterRequest(**payload.dict())
                user_data = self._prepare_student_data(student_payload, hashed_password)
                await self.user_repo.create_student(session, user_data, user_data["student_data"])
            elif payload.role == UserRole.TEACHER:
                teacher_payload = TeacherRegisterRequest(**payload.dict())
                user_data = self._prepare_teacher_data(teacher_payload, hashed_password)
                await self.user_repo.create_teacher(session, user_data, user_data["teacher_data"])
            else:
                raise HTTPException(status_code=400, detail="유효하지 않은 역할입니다.")

            return {"message": "회원가입이 완료되었습니다."}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error during user registration: {e}")
            raise HTTPException(status_code=500, detail="데이터베이스 오류가 발생했습니다.")

    def _prepare_student_data(self, payload: StudentRegisterRequest, hashed_password: str) -> dict:
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

    def _prepare_teacher_data(self, payload: TeacherRegisterRequest, hashed_password: str) -> dict:
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
        try:
            user = await self.user_repo.get_user_by_email(session, email)
            print(f"조회된 사용자: {user}")
            if user is None:
                print("404 에러: 등록되지 않은 이메일")
                raise HTTPException(status_code=404, detail="등록되지 않은 이메일입니다.")
            # 비활성화된 사용자 체크
            if user.deactivated_at:
                raise HTTPException(status_code=400, detail="비활성화된 사용자입니다. 계정을 복구하려면 지원팀에 문의해주세요.")

            if not verify_password(password, user.password):
                raise HTTPException(status_code=401, detail="비밀번호가 틀렸습니다.")

            role = str(user.role) if not isinstance(user.role, str) else user.role

            jti = str(uuid.uuid4())
            access_token = create_access_token(
                {"sub": str(user.id), "role": role, "jti": jti}, expires_delta=timedelta(minutes=45)  # 문자열로 변환된 role 사용
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
                max_age=REFRESH_TOKEN_TTL,
            )
            first_login = False
            if role == "student" and user.first_login:
                first_login = True
                user.first_login = False
                session.add(user)
                await session.commit()

            return {
                "id": user.id,
                "access_token": access_token,
                "refresh_token": refresh_token,  # 테스트 용
                "token_type": "Bearer",
                "expires_in": 45 * 60,
                "role": role,
                "first_login": first_login,  # 학생인 경우에만 의미 있는 값
                "message": "로그인에 성공하였습니다.",
            }
        except HTTPException as e:
            print(f"HTTPException 발생: {e}")
            raise e

    async def refresh_access_token(self, refresh_token: str, session: AsyncSession):
        if not refresh_token:
            raise HTTPException(status_code=401, detail="Refresh Token이 제공되지 않았습니다.")

        try:
            payload = verify_access_token(refresh_token)
            user_id = int(payload.get("sub", 0))
            if not user_id:
                raise HTTPException(status_code=401, detail="Refresh Token 정보가 유효하지 않습니다.")

            user = await self.user_repo.get_user_by_id(session, user_id)
            if not user:
                raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

            redis_key = get_redis_key_refresh_token(user_id)
            stored_refresh_token = await get_from_redis(redis_key)
            if not stored_refresh_token:
                raise HTTPException(status_code=401, detail="Refresh Token이 만료되었습니다.")
            if stored_refresh_token.strip() != refresh_token.strip():
                raise HTTPException(status_code=401, detail="Refresh Token이 유효하지 않습니다.")

            # Access Token 생성
            role = str(user.role) if not isinstance(user.role, str) else user.role
            jti = str(uuid.uuid4())
            access_token = create_access_token(
                {"sub": str(user.id), "role": role, "jti": jti},
                expires_delta=timedelta(minutes=45),
            )

            # Redis에 JTI 저장
            expiry = 45 * 60
            jti_key = get_redis_key_jti(jti)
            await save_to_redis(jti_key, "used", expiry)

            return {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": expiry,
                "message": "Access Token이 성공적으로 갱신되었습니다.",
            }

        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Refresh Token이 만료되었습니다.")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Refresh Token 유효하지 않습니다.")

    async def logout_user(self, access_token: str, response: Response):
        try:
            payload = verify_access_token(access_token)
            expiry = payload.get("exp")
            if expiry is None:
                raise HTTPException(status_code=400, detail="Access Token에 형식이 잘 못 되었습니다..")

            # 현재 KST 시간과 비교
            remaining_time = expiry - int(datetime.now().timestamp())
            if remaining_time < 0:
                raise HTTPException(status_code=401, detail="Access Token이 만료되었습니다.")

            jti = payload.get("jti")
            user_id = payload.get("sub")
            if not jti or not user_id:
                raise HTTPException(status_code=400, detail="Access Token에 형식이 잘 못 되었습니다.")

            # Redis에서 Refresh Token 삭제
            redis_key = get_redis_key_refresh_token(user_id)
            await delete_from_redis(redis_key)
            logger.info(f"Redis에서 사용자 {user_id}의 키 {redis_key} 삭제 완료.")

            await mark_jti_used(jti, remaining_time)

            # 쿠키 삭제
            response.delete_cookie(key="refresh_token")
            return {"message": "로그아웃이 완료되었습니다."}

        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Access Token이 만료되었습니다.")

    async def find_email_by_phone(self, phone: str, session: AsyncSession) -> dict:
        if not phone:
            raise HTTPException(status_code=400, detail="유효하지 않은 전화번호입니다.")
        try:
            email = await self.user_repo.get_user_email_by_phone(session, phone)

            if not email:
                raise HTTPException(status_code=404, detail="해당 번호로 등록된 유저를 찾을 수 없습니다.")

            masked_email = self._mask_email(email)  # 이메일 마스킹 처리
            return {"email": masked_email}

        except HTTPException as e:
            logger.error(f"이메일 검색 실패: {e.detail}")
            raise

    def _mask_email(self, email: str) -> str:
        try:
            local_part, domain_part = email.split("@")
            masked_local = local_part[0] + "***"
            return f"{masked_local}@{domain_part}"
        except Exception:
            raise HTTPException(status_code=400, detail="잘못된 이메일 형식입니다.")

    async def reset_password(self, email: str, session: AsyncSession) -> dict:
        temp_password = generate_temp_password()

        if not validate_temp_password_complexity(temp_password):
            raise HTTPException(status_code=500, detail="데이터베이스 오류가 발생했습니다.")

        await self.user_repo.reset_user_password(session, email, temp_password)

        logger.info(f"임시 비밀번호 발급 완료: {email}")
        return {
            "message": "임시 비밀번호가 발급되었습니다.",
            "email": email,
            "temp_password": temp_password,
        }

    async def checking_password(self, user_id: int, password: str, session: AsyncSession) -> dict:
        try:
            user = await self.user_repo.get_user_by_id(session, user_id)
            if not user:
                logger.error(f"사용자를 찾을 수 없습니다. user_id: {user_id}")
                raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

            if not verify_password(password, user.password):
                logger.error(f"비밀번호 검증 실패. user_id: {user_id}")
                raise HTTPException(status_code=401, detail="비밀번호가 일치하지 않습니다.")

            return {"message": "비밀번호 검증에 성공했습니다."}

        except HTTPException as e:
            raise

    async def update_user_info(self, user_id: int, role: str, update_data: dict, session: AsyncSession) -> dict:
        try:
            if "email" in update_data:
                try:
                    validate_email(update_data["email"])
                except EmailNotValidError as e:
                    logger.error(f"유효하지 않은 이메일 형식: {update_data['email']} - {str(e)}")
                    raise HTTPException(status_code=400, detail="유효하지 않은 이메일 형식입니다.")

            if "password" in update_data:
                if not validate_password_complexity(update_data["password"]):
                    logger.error(f"유효하지 않은 비밀번호 형식: {update_data['password']}")
                    raise HTTPException(status_code=400, detail="유효하지 않은 비밀번호 형식입니다.")
                if update_data["password"] != update_data.get("password_confirm"):
                    logger.error("비밀번호와 비밀번호 확인이 일치하지 않습니다.")
                    raise HTTPException(status_code=400, detail="비밀번호가 일치하지 않습니다.")
                update_data["password"] = hash_password(update_data["password"])
                del update_data["password_confirm"]

            if "phone" in update_data:
                phone = update_data["phone"]
                if not re.fullmatch(r"010\d{8}", phone):
                    logger.error(f"유효하지 않은 핸드폰 번호 형식: {phone}")
                    raise HTTPException(status_code=400, detail="유효하지 않은 핸드폰 번호 형식입니다.")

            common_fields = {key: update_data[key] for key in ("email", "phone", "password") if key in update_data}

            if role == "teacher":
                await self.user_repo.update_teacher_info(session, user_id, common_fields)
            elif role == "student":
                student_fields = {key: update_data[key] for key in ("school", "grade") if key in update_data}
                await self.user_repo.update_student_info(session, user_id, common_fields, student_fields)
            else:
                logger.error(f"잘못된 역할 지정: role={role}")
                raise HTTPException(status_code=400, detail="잘못된 역할입니다.")

            logger.info(f"사용자 정보 업데이트 성공: user_id={user_id}, role={role}")
            return {"message": "회원 정보가 성공적으로 변경되었습니다."}

        except HTTPException as e:
            logger.error(f"사용자 정보 업데이트 실패: {e.detail}")
            raise

    async def get_all_teachers_info(self, session: AsyncSession) -> list[dict]:
        try:
            teachers = await self.user_repo.get_all_teachers_info(session)
            if not teachers:
                logger.warning("교사 정보가 존재하지 않습니다.")
                raise HTTPException(status_code=404, detail="교사 정보가 존재하지 않습니다.")
            return teachers

        except Exception as e:
            logger.error(f"예상치 못한 오류 발생: {e}")
            raise HTTPException(status_code=500, detail="데이터베이스 오류가 발생했습니다.")

    # 학생 최초 로그인 시 교사 선택
    async def create_study_group(self, session: AsyncSession, current_user: dict, teacher_id: int, teacher_name: str) -> dict:
        logger.info(f"Creating study group for user_id={current_user['user_id']}")

        if current_user["role"].upper() != "STUDENT":
            logger.warning(f"Unauthorized role: {current_user['role']}")
            raise HTTPException(status_code=403, detail="학생만 스터디 그룹을 생성할 수 있습니다.")

        try:
            student_id = await self.user_repo.get_student_id(session, current_user["user_id"])
            if not student_id:
                logger.warning(f"No student found for user_id={current_user['user_id']}")
                raise HTTPException(status_code=404, detail="학생 정보를 찾을 수 없습니다.")
        except Exception as e:
            logger.error(f"Error fetching student ID: {e}")
            raise HTTPException(status_code=500, detail="데이터베이스 오류가 발생했습니다.")

        try:
            fetched_teacher_id = await self.user_repo.get_teacher_by_id_and_name(session, teacher_id, teacher_name)
            if not fetched_teacher_id:
                logger.warning(f"Teacher not found or name mismatch: teacher_id={teacher_id}, name={teacher_name}")
                raise HTTPException(status_code=404, detail="선생님 정보를 찾을 수 없습니다.")
        except Exception as e:
            logger.error(f"Error fetching teacher: {e}")
            raise HTTPException(status_code=500, detail="데이터베이스 오류가 발생했습니다.")

        try:
            new_group = await self.user_repo.create_study_group(session, student_id, teacher_id)
            logger.info(f"Study group created: {new_group}")
            return {"message": "study group이 성공적으로 생성되었습니다."}
        except Exception as e:
            logger.error(f"Error creating study group: {e}")
            raise HTTPException(status_code=500, detail="데이터베이스 오류가 발생했습니다.")

    # 남이 내 프로필 조회
    async def get_user_profile_by_id(self, user_id: int, session: AsyncSession):
        try:
            user = await self.user_repo.get_user_with_profile(user_id, session)
            if not user:
                raise HTTPException(status_code=404, detail="사용자 정보를 찾을 수 없습니다.")

            if not user.tag or not user.tag.nickname:
                raise HTTPException(status_code=400, detail="사용자의 닉네임이 설정되지 않았습니다.")

            posts = await self.user_repo.get_posts_by_user(user_id, session)
            posts_data = [
                PostResponse(
                    post_id=post_datas["external_id"],
                    post_image=post_datas["images"][0] if post_datas["images"] else None,
                )
                for post_datas in posts.values()
            ]
            # like_count와 comment_count 계산
            like_count = sum(post_data['post'].like_count for post_data in posts.values())  # 'post' 객체에서 like_count 접근
            comment_count = sum(post_data['post'].comment_count for post_data in posts.values())  # 'post' 객체에서 comment_count 접근

            role=user.role
            common_data = CommonProfileResponse(
                role=role,
                id=user.id,
                nickname=user.tag.nickname,
                profile_image=user.profile_image,
                post_count=len(posts_data),
                like_count=like_count,
                comment_count=comment_count,
            )
            # 학생 프로필 생성
            if role == UserRole.STUDENT.value:
                if not user.student:
                    raise HTTPException(status_code=404, detail="학생 정보를 찾을 수 없습니다.")
                student_profile = StudentProfileResponse(
                    **common_data.dict(),
                    school=user.student.school,
                    grade=f"{user.student.grade}학년",
                    career_aspiration=user.student.career_aspiration,
                    interest=user.student.interest,
                    description=user.student.description,
                    posts=posts_data,
                )
                return student_profile

            # 교사 프로필 생성
            elif role == UserRole.TEACHER.value:
                if not user.teacher or not user.teacher.organization:
                    raise HTTPException(status_code=404, detail="교사 정보를 찾을 수 없습니다.")
                teacher_profile = TeacherProfileResponse(
                    **common_data.dict(),
                    organization_name=user.teacher.organization.name,
                    organization_type=user.teacher.organization.type,
                    position=user.teacher.organization.position,
                    posts=posts_data,
                )
                return teacher_profile

            else:
                raise HTTPException(status_code=400, detail="올바르지 않은 역할입니다.")

        except Exception as e:
            logger.error(f"Error fetching profile for user_id={user_id}: {e}")
            raise HTTPException(status_code=500, detail="데이터베이스 오류가 발생했습니다.")

    # 내가 내 프로필 조회
    async def get_my_profile(self, user_id: int, role: str, session: AsyncSession):

        if role not in [UserRole.STUDENT.value, UserRole.TEACHER.value]:
            raise HTTPException(status_code=400, detail="유효하지 않은 역할입니다.")

        user = await self.user_repo.get_user_with_profile(user_id, session)
        if not user:
            raise HTTPException(status_code=404, detail="사용자 정보를 찾을 수 없습니다.")

        if not user.tag or not user.tag.nickname:
            raise HTTPException(status_code=400, detail="사용자의 닉네임이 설정되지 않았습니다.")

        posts = await self.user_repo.get_posts_by_user(user_id, session)
        posts_data = [
            PostResponse(
                post_id=post_datas["external_id"],
                post_image=post_datas["images"][0] if post_datas["images"] else None,
            )
            for post_datas in posts.values()
        ]

        # like_count와 comment_count 계산
        like_count = sum(post_data['post'].like_count for post_data in posts.values())  # 'post' 객체에서 like_count 접근
        comment_count = sum(post_data['post'].comment_count for post_data in posts.values())  # 'post' 객체에서 comment_count 접근

        common_data = CommonProfileResponse(
            role=role,
            id=user.id,
            nickname=user.tag.nickname,
            profile_image=user.profile_image,
            post_count=len(posts_data),
            like_count=like_count,
            comment_count=comment_count,
        )

        logger.debug(f"Common data: {common_data}")
        logger.debug(f"Posts data: {posts_data}")

        # 학생 프로필 생성
        if role == UserRole.STUDENT.value:
            if not user.student:
                raise HTTPException(status_code=404, detail="학생 정보를 찾을 수 없습니다.")
            student_profile = StudentProfileResponse(
                **common_data.dict(),
                school=user.student.school,
                grade=f"{user.student.grade}학년",
                career_aspiration=user.student.career_aspiration,
                interest=user.student.interest,
                description=user.student.description,
                posts=posts_data,
            )
            logger.debug(f"Student profile: {student_profile}")
            return student_profile

        # 교사 프로필 생성
        elif role == UserRole.TEACHER.value:
            if not user.teacher or not user.teacher.organization:
                raise HTTPException(status_code=404, detail="교사 정보를 찾을 수 없습니다.")
            teacher_profile = TeacherProfileResponse(
                **common_data.dict(),
                organization_name=user.teacher.organization.name,
                organization_type=user.teacher.organization.type,
                position=user.teacher.organization.position,
                posts=posts_data,
            )
            logger.debug(f"Teacher profile: {teacher_profile}")
            return teacher_profile

        else:
            raise HTTPException(status_code=400, detail="올바르지 않은 역할입니다.")

    async def update_student_profile(self, user_id: int, update_data: dict, session: AsyncSession) -> dict:
        user = await self.user_repo.get_students_profile(user_id, session)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if "nickname" in update_data:
            if user.tag:
                user.tag.nickname = update_data["nickname"]
            else:
                new_tag = Tag(user_id=user.id, nickname=update_data["nickname"])
                session.add(new_tag)

        if "profile_image" in update_data:
            user.profile_image = update_data["profile_image"]

        if user.student:
            student = user.student
        else:
            student = Student(user_id=user.id)
            session.add(student)

        if "career_aspiration" in update_data:
            student.career_aspiration = update_data["career_aspiration"]
        if "interest" in update_data:
            student.interest = update_data["interest"]
        if "description" in update_data:
            student.description = update_data["description"]

        await session.commit()

        return {"message": "학생 프로필이 성공적으로 업데이트되었습니다."}

    # 교사 프로필 업데이트
    async def update_teacher_profile(self, user_id: int, update_data: dict, session: AsyncSession) -> dict:
        user = await self.user_repo.get_teachers_profile(user_id, session)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if "nickname" in update_data:
            if user.tag:
                user.tag.nickname = update_data["nickname"]
            else:
                new_tag = Tag(user_id=user.id, nickname=update_data["nickname"])
                session.add(new_tag)

        if "profile_image" in update_data:
            user.profile_image = update_data["profile_image"]

        if user.teacher and user.teacher.organization:
            organization = user.teacher.organization
        else:
            if not user.teacher:
                teacher = Teacher(user_id=user.id)
                session.add(teacher)
                user.teacher = teacher

            organization = Organization(teacher=user.teacher)
            session.add(organization)

        if "organization_name" in update_data:
            organization.name = update_data["organization_name"]
        if "organization_type" in update_data:
            organization.type = update_data["organization_type"]
        if "organization_position" in update_data:
            organization.position = update_data["organization_position"]

        await session.commit()

        return {"message": "선생님 프로필이 성공적으로 업데이트되었습니다."}

    # 탈퇴하기 -> deactivated_at 30일 후 삭제
    async def deactivate_user_service(self, user_id, session: AsyncSession) -> dict:
        try:
            print(f"Fetching user with id: {user_id}")
            user = await self.user_repo.get_user_by_id(session, user_id)

            if user is None:
                print("User not found.")
                raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

            print(f"Checking if user {user.id} is already deactivated...")
            if user.deactivated_at:
                print("User is already deactivated.")
                raise HTTPException(status_code=400, detail="이미 비활성화된 사용자입니다.")

            # 비활성화 날짜를 현재 시간으로 설정
            print(f"Deactivating user {user.id}...")
            user.deactivated_at = datetime.now()
            session.add(user)
            await session.commit()

            print(f"User {user.id} deactivated successfully.")
            return {"message": "탈퇴되었습니다. 해당 계정 복구를 원하시면 30일 이내로 문의주세요."}

        except HTTPException as e:
            print(f"HTTP Exception occurred: {str(e)}")
            raise e

        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            print(f"Exception traceback: {e.__traceback__}")
            raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

    # 30일 이상 비활성화된 사용자를 스케줄러로 삭제로직 예정
