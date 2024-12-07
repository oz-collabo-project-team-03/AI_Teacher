import os
import pdb
import uuid
from datetime import timedelta
import httpx
import jwt
import requests  # type: ignore
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession, async_session
from ulid import ulid  # type: ignore

from src.app.common.utils.consts import SocialProvider, UserRole
from src.app.common.utils.dependency import get_session
from src.app.common.utils.redis_utils import save_to_redis, get_redis_key_refresh_token, get_redis_key_jti, get_from_redis
from src.app.common.utils.security import create_refresh_token, create_access_token, verify_access_token
from src.app.common.utils.verify_password import generate_random_social_password
from src.app.v1.auth.repository.oauth_repository import OAuthRepository
from src.app.v1.auth.schema.requestDto import (
    SocialLoginStudentRequest,
    SocialLoginTeacherRequest,
)
from src.app.v1.user.entity.organization import Organization
from src.app.v1.user.entity.student import Student
from src.app.v1.user.entity.teacher import Teacher
from src.app.v1.user.entity.user import User
from src.app.v1.user.repository.user_repository import UserRepository
from src.app.v1.auth.schema.requestDto import SocialLoginStudentRequest, SocialLoginTeacherRequest
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()


class OAuthService:
    def __init__(self, oauth_repo: OAuthRepository, user_repo: UserRepository):
        self.oauth_repo = oauth_repo
        self.user_repo = user_repo
        # 환경 변수 로드
        self.KAKAO_CLIENT_ID = os.getenv("KAKAO_CLIENT_ID")
        self.KAKAO_CLIENT_SECRET = os.getenv("KAKAO_CLIENT_SECRET")
        self.KAKAO_REDIRECT_URI = os.getenv("KAKAO_REDIRECT_URI")

        self.GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
        self.GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
        self.GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

        self.NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
        self.NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
        self.NAVER_REDIRECT_URI = os.getenv("NAVER_REDIRECT_URI")

    # 공통 함수: OAuth 요청 URL 생성
    def get_oauth_url(self, provider: str):
        if provider == "kakao":
            oauth_url = (
                f"https://kauth.kakao.com/oauth/authorize?"
                f"client_id={self.KAKAO_CLIENT_ID}&"
                f"redirect_uri={self.KAKAO_REDIRECT_URI}&"
                f"response_type=code"
            )
            print(f"Generated Kakao OAuth URL: {oauth_url}")
            return oauth_url
        elif provider == "google":
            oauth_url = (
                f"https://accounts.google.com/o/oauth2/auth?"
                f"client_id={self.GOOGLE_CLIENT_ID}&"
                f"redirect_uri={self.GOOGLE_REDIRECT_URI}&"
                f"response_type=code&"
                f"scope=email%20profile"
            )
            print(f"Generated Google OAuth URL: {oauth_url}")
            return oauth_url
        elif provider == "naver":
            oauth_url = (
                f"https://nid.naver.com/oauth2.0/authorize?"
                f"client_id={self.NAVER_CLIENT_ID}&"
                f"redirect_uri={self.NAVER_REDIRECT_URI}&"
                f"response_type=code"
            )
            print(f"Generated Naver OAuth URL: {oauth_url}")
            return oauth_url
        else:
            print(f"Unsupported provider: {provider}")
            raise HTTPException(status_code=400, detail="지원하는 소셜로그인이 아닙니다.")

    # 공통 함수: Access Token 요청
    async def get_access_token(self, provider: str, code: str):
        if provider == "kakao":
            token_url = "https://kauth.kakao.com/oauth/token"
            data = {
                "grant_type": "authorization_code",
                "client_id": self.KAKAO_CLIENT_ID,
                "client_secret": self.KAKAO_CLIENT_SECRET,
                "redirect_uri": self.KAKAO_REDIRECT_URI,
                "code": code,
            }
        elif provider == "google":
            token_url = "https://oauth2.googleapis.com/token"
            data = {
                "grant_type": "authorization_code",
                "client_id": self.GOOGLE_CLIENT_ID,
                "client_secret": self.GOOGLE_CLIENT_SECRET,
                "redirect_uri": self.GOOGLE_REDIRECT_URI,
                "code": code,
            }
        elif provider == "naver":
            token_url = "https://nid.naver.com/oauth2.0/token"
            data = {
                "grant_type": "authorization_code",
                "client_id": self.NAVER_CLIENT_ID,
                "client_secret": self.NAVER_CLIENT_SECRET,
                "redirect_uri": self.NAVER_REDIRECT_URI,
                "code": code,
            }
        else:
            raise HTTPException(status_code=400, detail="Unsupported provider")

        async with httpx.AsyncClient() as client:
            print(f"Requesting access token from {token_url} with data: {data}")
            response = await client.post(token_url, data=data)
            if response.status_code != 200:
                print(f"Error fetching access token: {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to get access token: {response.text}",
                )
            token_data = response.json()

            if "refresh_token" not in token_data:
                print("Warning: Refresh token이 반환값에 포함되어있지 않습니다..")

            return token_data

    async def get_user_info(self, provider: str, access_token: str) -> dict:
        provider_urls = {
            "kakao": "https://kapi.kakao.com/v2/user/me",
            "google": "https://www.googleapis.com/oauth2/v2/userinfo",
            "naver": "https://openapi.naver.com/v1/nid/me",
        }

        if provider not in provider_urls:
            raise HTTPException(status_code=400, detail="지원하지 않는 provider입니다.")

        user_info_url = provider_urls[provider]
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(user_info_url, headers=headers)
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to fetch user info: {response.text}",
                )

            user_data = response.json()
            logger.info(f"Fetched user data from {provider}: {user_data}")
        return self.map_user_info(provider, user_data)

    def map_user_info(self, provider: str, user_data: dict) -> dict:
        try:
            if provider == "kakao":
                return {
                    "id": user_data.get("id"),
                    "email": user_data.get("kakao_account", {}).get("email"),
                    "phone": user_data.get("kakao_account", {}).get("phone_number"),
                }
            elif provider == "google":
                return {
                    "id": user_data.get("id"),
                    "email": user_data.get("email"),
                    "phone": user_data.get("phone"),
                }
            elif provider == "naver":
                response_data = user_data.get("response", {})
                return {
                    "id": response_data.get("id"),
                    "email": response_data.get("email"),
                    "phone": response_data.get("mobile"),
                }
            else:
                raise HTTPException(status_code=400, detail="지원하지 않는 provider입니다.")
        except KeyError as e:
            raise HTTPException(status_code=500, detail=f"사용자 데이터 구문 분석 오류{e}")

    async def login_social_user(self, saved_user: User, response: Response, session: AsyncSession):
        # pdb.set_trace()

        external_id = saved_user.external_id
        jti = str(uuid.uuid4())
        access_token = create_access_token({"sub": saved_user.id, "jti": jti, "role": saved_user.role}, expires_delta=timedelta(minutes=45))
        refresh_token = create_refresh_token({"sub": saved_user.id}, expires_delta=timedelta(days=7))
        await save_to_redis(get_redis_key_jti(jti), "used", 45 * 60)
        await save_to_redis(get_redis_key_refresh_token(saved_user.id), refresh_token, expiry=7 * 24 * 3600)

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="Strict",  # type: ignore
            max_age=7 * 24 * 3600,
        )

        first_login = saved_user.first_login
        social = saved_user.social_provider is not None

        return {
            "id": saved_user.id,
            "role": saved_user.role,
            "access_token": access_token,
            "refresh_token": refresh_token,  # 테스트 용
            "token_type": "Bearer",
            "expires_in": 45 * 60,
            "first_login": first_login,
            "social": social,
            "message": "소셜 로그인에 성공했습니다.",
        }

    async def save_user_info(self, provider: str, user_info: dict, session: AsyncSession):
        role = user_info.get("role", UserRole.STUDENT)
        # pdb.set_trace()
        user = await self.oauth_repo.get_user_by_email(
            session=session,
            email=user_info["email"],
        )

        if not user:
            phone = user_info.get("phone")
            formatted_phone = self.oauth_repo.format_phone_number(phone, provider)

            user = User(
                external_id=ulid(),  # type: ignore
                email=user_info.get("email"),
                phone=formatted_phone,
                password=generate_random_social_password(),
                role=role,
                social_provider=provider,
                is_privacy_accepted=True,
            )
            session.add(user)
            await session.commit()
        return user

    async def update_student_info(self, payload: SocialLoginStudentRequest, user_id: int, session: AsyncSession):
        user = await self.oauth_repo.get_user_with_info(user_id, session)
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

        if not user.first_login:
            raise HTTPException(status_code=400, detail="이미 2번 이상 로그인을 진행한 사용자입니다.")

        updated_user = await self.oauth_repo.update_student(user_id, payload.dict(), session)

        # 선생님과 연결 여부 확인
        is_connected_to_teacher = await self.oauth_repo.is_student_connected_to_teacher(updated_user.student.id, session)

        return {
            "role": updated_user.role.value,
            "first_login": updated_user.first_login,
            "study_group": is_connected_to_teacher,
            "message": "학생 회원정보가 성공적으로 업데이트되었습니다.",
        }

    async def update_teacher_info(self, payload: SocialLoginTeacherRequest, user_id: int, session: AsyncSession):
        user = await self.oauth_repo.get_user_with_info(user_id, session)
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

        if not user.first_login:
            raise HTTPException(status_code=400, detail="이미 2번 이상 로그인을 진행한 사용자입니다.")

        user.role = UserRole.TEACHER

        updated_user = await self.oauth_repo.update_teacher(user_id, payload.dict(), session)

        return {
            "role": updated_user.role.value,
            "first_login": updated_user.first_login,
            "message": "선생님 회원정보가 성공적으로 업데이트되었습니다.",
        }
