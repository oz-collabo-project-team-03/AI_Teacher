import os
from datetime import datetime

import requests  # type: ignore
from dotenv import load_dotenv
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.common.utils.consts import UserRole, SocialProvider
from src.app.v1.auth.repository.oauth_repository import OAuthRepository
from src.app.v1.user.repository.user_repository import UserRepository


load_dotenv()


class OAuthService:
    def __init__(self, oauth_repo: OAuthRepository):
        self.oauth_repo = oauth_repo
        # 환경 변수 로드
        self.KAKAO_CLIENT_ID = os.getenv("KAKAO_CLIENT_ID")
        self.KAKAO_CLIENT_SECRET = os.getenv("KAKAO_CLIENT_SECRET")
        self.DEV_KAKAO_REDIRECT_URI = os.getenv("DEV_KAKAO_REDIRECT_URI")
        self.KAKAO_REDIRECT_URI = os.getenv("KAKAO_REDIRECT_URI")

        self.GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
        self.GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
        self.DEV_GOOGLE_REDIRECT_URI = os.getenv("DEV_GOOGLE_REDIRECT_URI")
        self.GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

        self.NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
        self.NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
        self.DEV_NAVER_REDIRECT_URI = os.getenv("DEV_NAVER_REDIRECT_URI")
        self.NAVER_REDIRECT_URI = os.getenv("NAVER_REDIRECT_URI")

    # 공통 함수: OAuth 요청 URL 생성
    def get_oauth_url(self, provider: str):
        if provider == "kakao":
            return (
                f"https://kauth.kakao.com/oauth/authorize?"
                f"client_id={self.KAKAO_CLIENT_ID}&"
                f"redirect_uri={self.DEV_KAKAO_REDIRECT_URI}&"
                f"response_type=code"
            )
        elif provider == "google":
            return (
                f"https://accounts.google.com/o/oauth2/auth?"
                f"client_id={self.GOOGLE_CLIENT_ID}&"
                f"redirect_uri={self.DEV_GOOGLE_REDIRECT_URI}&"
                f"response_type=code&"
                f"scope=email%20profile"
            )
        elif provider == "naver":
            return (
                f"https://nid.naver.com/oauth2.0/authorize?"
                f"client_id={self.NAVER_CLIENT_ID}&"
                f"redirect_uri={self.DEV_NAVER_REDIRECT_URI}&"
                f"response_type=code"
            )
        else:
            raise HTTPException(status_code=400, detail="지원하는 소셜로그인이 아닙니다.")

    # 공통 함수: Access Token 요청
    def get_access_token(self, provider: str, code: str):
        if provider == "kakao":
            token_url = "https://kauth.kakao.com/oauth/token"
            data = {
                "grant_type": "authorization_code",
                "client_id": self.KAKAO_CLIENT_ID,
                "client_secret": self.KAKAO_CLIENT_SECRET,
                "redirect_uri": self.DEV_KAKAO_REDIRECT_URI,
                "code": code,
            }
        elif provider == "google":
            token_url = "https://oauth2.googleapis.com/token"
            data = {
                "grant_type": "authorization_code",
                "client_id": self.GOOGLE_CLIENT_ID,
                "client_secret": self.GOOGLE_CLIENT_SECRET,
                "redirect_uri": self.DEV_GOOGLE_REDIRECT_URI,
                "code": code,
            }
        elif provider == "naver":
            token_url = "https://nid.naver.com/oauth2.0/token"
            data = {
                "grant_type": "authorization_code",
                "client_id": self.NAVER_CLIENT_ID,
                "client_secret": self.NAVER_CLIENT_SECRET,
                "redirect_uri": self.DEV_NAVER_REDIRECT_URI,
                "code": code,
            }
        else:
            raise HTTPException(status_code=400, detail="Unsupported provider")

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = requests.post(token_url, headers=headers, data=data)
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to get access token: {response.text}",
            )
        return response.json()

        # 공통 함수: 사용자 정보 요청

    def get_user_info(self, provider: str, access_token: str):
        if provider == "kakao":
            user_info_url = "https://kapi.kakao.com/v2/user/me"
            headers = {"Authorization": f"Bearer {access_token}"}
        elif provider == "google":
            user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
            headers = {"Authorization": f"Bearer {access_token}"}
        elif provider == "naver":
            user_info_url = "https://openapi.naver.com/v1/nid/me"
            headers = {"Authorization": f"Bearer {access_token}"}
        else:
            raise HTTPException(status_code=400, detail="Unsupported provider")

        response = requests.get(user_info_url, headers=headers)
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to get user info: {response.text}",
            )
        return response.json()
    # async def save_user(self, session: AsyncSession, user_info: dict, role: UserRole):
    #
    #     kakao_id = user_info["id"]
    #     kakao_account = user_info["kakao_account"]
    #
    #     email = kakao_account.get("email")
    #     phone = kakao_account.get("phone_number")
    #
    #     user = await UserRepository.get_user_by_external_id(
    #         session, external_id=str(kakao_id), social_provider=SocialProvider.KAKAO
    #     )
    #
    #     if not user:
    #         user = await UserRepository.create_user(
    #             session,
    #             external_id=str(kakao_id),
    #             email=email,
    #             phone=phone,
    #             role=role,
    #             social_provider=SocialProvider.KAKAO,
    #         )
    #
    #         if role == UserRole.STUDENT:
    #             await UserRepository.create_student(session, user.id)
    #         elif role == UserRole.TEACHER:
    #             await UserRepository.create_teacher(session, user.id)
    #     else:
    #         user = await UserRepository.update_user(session, user, email=email, phone=phone)
    #
    #     try:
    #         await session.commit()
    #         return user
    #     except IntegrityError:
    #         await session.rollback()
    #         raise HTTPException(status_code=400, detail="사용자를 저장하지 못했습니다.")