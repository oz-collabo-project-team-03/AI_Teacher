# import logging
# import os
# import uuid
# from datetime import timedelta
#
# from fastapi import HTTPException, Response
# from sqlalchemy.ext.asyncio import AsyncSession
#
# from src.app.common.utils.consts import SocialProvider
#
# # from src.app.common.utils.redis import (
# #     delete_from_redis,
# #     get_from_redis,
# #     get_redis_key_jti,
# #     get_redis_key_refresh_token,
# #     save_to_redis,
# # )
# from src.app.common.utils.security import create_access_token, create_refresh_token
# from src.app.v1.auth.repository.auth_repository import AuthRepository
#
# # from src.app.v1.auth.service.kakao_service import KakaoService
#
# logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO)
#
# SECURE_COOKIE = os.getenv("SECURE_COOKIE", "false").lower() == "true"
#
#
# class AuthService:
#     def __init__(self):
#         self.kakao_service = KakaoService()
#         self.auth_repo = AuthRepository()
#
#     # kakao 로그인 URL 생성
#     def get_kakao_login_url(self):
#         return self.kakao_service.get_auth_url()
#
#     # 로그인
#     async def kakao_login(self, session: AsyncSession, code: str, response: Response):
#         # kakao 인가 코드 -> access, refresh 토큰
#         kakao_token = self.kakao_service.exchange_token(code)
#         kakao_access_token = kakao_token["access_token"]
#         kakao_refresh_token = kakao_token["refresh_token"]
#
#         # kakao 사용자 정보 가져오기
#         user_info = self.kakao_service.get_kakao_user_info(kakao_access_token)
#         external_id = str(user_info["id"])
#
#         # external_id와 social_provider로 사용자 조회
#         user = await self.auth_repo.get_user_by_external_id(session, external_id=external_id, provider=SocialProvider.KAKAO)
#
#         # 사용자 없으면 생성
#         if not user:
#             user_data = {
#                 "nickname": user_info["kakao_account"]["profile"]["nickname"],
#             }
#             user = await self.auth_repo.create_social_user(session, external_id=external_id, provider=SocialProvider.KAKAO, user_data=user_data)
#             # 4. 서비스 전용 Access Token 및 Refresh Token 생성
#             jti = str(uuid.uuid4())
#             service_access_token = create_access_token({"sub": str(user.id), "role": str(user.role), "jti": jti}, expires_delta=timedelta(minutes=15))
#             service_refresh_token = create_refresh_token({"sub": str(user.id)}, expires_delta=timedelta(days=7))
#
#             # 5. Redis에 토큰 저장
#             expiry = 15 * 60
#             await save_to_redis(get_redis_key_jti(jti), "used", expiry)
#             await save_to_redis(get_redis_key_refresh_token(user.id), service_refresh_token, expiry=7 * 24 * 3600)
#
#             # 6. 클라이언트에 토큰 반환
#             response.set_cookie(
#                 key="refresh_token",
#                 value=service_refresh_token,
#                 httponly=True,
#                 secure=SECURE_COOKIE,
#                 samesite="Strict",  # type: ignore
#                 max_age=7 * 24 * 3600,
#             )
#             return {
#                 "access_token": service_access_token,
#                 "refresh_token": service_refresh_token,
#                 "token_type": "Bearer",
#                 "expires_in": 900,
#                 "message": "소셜 로그인에 성공하였습니다.",
#             }
#
#     async def additional_social_infomation(self, payload, session: AsyncSession, role: str):
#
#         user = await self.auth_repo.get_user_by_external_id(session, payload.external_id)
#         if not user:
#             raise HTTPException(status_code=404, detail="해당 유저를 찾을 수 없습니다.")
#
#         # 데이터 업데이트
#         if role == "STUDENT":
#             user_data = {
#                 "phone": payload.phone,
#                 "is_privacy_accepted": payload.is_privacy_accepted,
#                 "role": role,
#                 "student_data": {
#                     "school": payload.school,
#                     "grade": payload.grade,
#                     "career_aspiration": payload.career_aspiration,
#                     "interest": payload.interests,
#                 },
#             }
#             await self.auth_repo.create_student(session, user_data)
#
#         elif role == "TEACHER":
#             user_data = {
#                 "phone": payload.phone,
#                 "is_privacy_accepted": payload.is_privacy_accepted,
#                 "role": role,
#                 "teacher_data": {
#                     "organization_name": payload.organization_name,
#                     "organization_type": payload.organization_type,
#                     "position": payload.position,
#                 },
#             }
#             await self.auth_repo.create_teacher(session, user_data)
#         else:
#             raise HTTPException(status_code=400, detail="유효하지 않은 역할입니다.")
#
#         return {"message": "사용자 정보가 성공적으로 업데이트되었습니다."}
