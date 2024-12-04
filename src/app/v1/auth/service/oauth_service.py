import os
import pdb
import uuid
from datetime import datetime, timedelta
from typing import Union

import httpx
import jwt
import requests  # type: ignore
from dotenv import load_dotenv
from fastapi import HTTPException, Depends
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from ulid import ulid  # type: ignore

from src.app.common.utils.consts import UserRole, SocialProvider
from src.app.common.utils.dependency import get_session
from src.app.common.utils.redis_utils import save_to_redis, get_redis_key_refresh_token, get_redis_key_jti, \
    get_from_redis
from src.app.common.utils.security import create_refresh_token, create_access_token, verify_access_token
from src.app.v1.auth.repository.oauth_repository import OAuthRepository
from src.app.v1.user.entity.organization import Organization
from src.app.v1.user.entity.student import Student
from src.app.v1.user.entity.teacher import Teacher
from src.app.v1.user.entity.user import User
from src.app.v1.user.repository.user_repository import UserRepository
from src.app.v1.auth.schema.requestDto import SocialLoginStudentRequest, SocialLoginTeacherRequest

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

        return self.map_user_info(provider, user_data)

    def map_user_info(self, provider: str, user_data: dict) -> dict:
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

    async def login_social_user(self, saved_user: User, response: Response):

        external_id = saved_user.external_id
        jti = str(uuid.uuid4())
        access_token = create_access_token(
            {"sub": saved_user.id, "jti": jti}, expires_delta=timedelta(minutes=45)
        )
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

        return {
            "external_id": external_id,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": 45 * 60,
            "message": "소셜 로그인에 성공했습니다.",
        }

        if saved_user.deactivated_at:
            raise HTTPException(status_code=400, detail="비활성화된 사용자입니다.")

        jti = str(uuid.uuid4())
        access_token = create_access_token(
            {"sub": saved_user.id, "jti": jti}, expires_delta=timedelta(minutes=45)
        )
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

        return {
            "id": saved_user.id,
            "access_token": access_token,
            "refresh_token": refresh_token, # 테스트용
            "token_type": "Bearer",
            "expires_in": 45 * 60,
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

            user = User(
                external_id=ulid(),
                email=user_info.get("email"),
                phone=self.oauth_repo.format_phone_number(str(user_info.get("phone"))),
                password="SOCIAL_LOGIN",
                role=role,
                social_provider=provider,
                is_privacy_accepted=True,
            )
            session.add(user)
            await session.commit()
        return user

    async def additional_user_info(
            self,
            payload: Union[SocialLoginStudentRequest, SocialLoginTeacherRequest],
            session: AsyncSession,
            user_id: int,
    ):
        try:
            user = await self.oauth_repo.get_user_by_id(session=session, user_id=user_id)
            if not user:
                raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

            if user.first_login is False:
                raise HTTPException(status_code=400, detail="이미 2번 이상 로그인을 진행한 사용자입니다.")

            if payload.role == UserRole.STUDENT:
                student_payload = SocialLoginStudentRequest(**payload.dict())
                user_data = self._prepare_student_data(student_payload)
                updated_user = await self.oauth_repo.update_student(user_id, user_data, session)

            elif payload.role == UserRole.TEACHER:
                teacher_payload = SocialLoginTeacherRequest(**payload.dict())
                user_data = self._prepare_teacher_data(teacher_payload)
                updated_user = await self.oauth_repo.update_teacher(user_id, user_data, session)

            else:
                raise HTTPException(status_code=400, detail="유효하지 않은 역할입니다.")

            # updated_user.first_login =False
            session.add(updated_user)
            await session.commit()

            return {"message": "추가 회원 정보가 저장되었습니다."}

        except HTTPException:
            raise
        except IntegrityError as e:
            raise HTTPException(status_code=500, detail=f"데이터베이스 오류가 발생했습니다.{str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def _prepare_student_data(self, payload: SocialLoginStudentRequest) -> dict:
        return {
            "role": UserRole.STUDENT,
            "is_privacy_accepted": payload.is_privacy_accepted,
            "student_data": {
                "school": payload.school,
                "grade": payload.grade,
                "career_aspiration": payload.career_aspiration,
                "interest": payload.interests,
            },
            "nickname": payload.nickname,
        }

    def _prepare_teacher_data(self, payload: SocialLoginTeacherRequest) -> dict:
        return {
            "role": UserRole.TEACHER,
            "is_privacy_accepted": payload.is_privacy_accepted,
            "teacher_data": {
                "organization_name": payload.organization_name,
                "organization_type": payload.organization_type,
                "position": payload.position,
            },
            "nickname": payload.nickname,
        }
