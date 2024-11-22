# from fastapi import HTTPException, Response, status
# from redis.exceptions import RedisError
# from sqlalchemy.ext.asyncio import AsyncSession
#
# from src.app.v1.auth.schema.responseDto import (
#     KakaoOauthErrorResponse,
#     KakaoOauthResponse,
# )
# from src.app.v1.user.entity.user import User
# from src.app.v1.user.repository.user_repository import UserRepository
#
# user_repository = UserRepository()
#
#
# async def login_kakao_service(code: str, session: AsyncSession, response: Response) -> KakaoOauthResponse:
#     access_token = await get_kakao_token(code)
#     if not access_token:
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="카카오 로그인이 실패했습니다.")
#
#     kakao_user = await get_kakao_user_info(access_token)
#     if not kakao_user:
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="카카오 사용자 정보 조회를 실패하였습니다.")
#
#     kakao_id = kakao_user.get("id")
#     email = kakao_user.get("kakao_account", {}).get("email")
#     nickname = kakao_user.get("properties", {}).get("nickname")
#     phone = kakao_user.get("kakao_account", {}).get("phone_number")
#     image_url = kakao_user.get("properties", {}).get("thumbnail_image")
#
#     user = await user_repository.get_kakao_user(oauth_id=kakao_id, session=session)
#
#     if user:
#         return await _process_existing_user(user, session, response)
#     else:
#         return await _process_new_user(kakao_id, email, nickname, phone, image_url, response)
#
#
# async def _process_existing_user(user, session: AsyncSession, response: Response) -> KakaoOauthResponse:
#     jwt_access_token, jwt_refresh_token, jti = await _generate_and_store_tokens(user.id)
#     _set_refresh_token_cookie(response, jwt_refresh_token)
#
#     return KakaoOauthResponse(
#         access_token=jwt_access_token,
#         id=user.id,
#         profile_image_url=user.image_url,
#     )
#
#
# async def _process_new_user(kakao_id: int, email: str, nickname: str, image_url: str, phone: str, response: Response) -> KakaoOauthResponse:
#     try:
#         user = await user_repository.create_user(oauth_id=kakao_id, email=email, nickname=nickname, phone=phone, image_url=image_url)
#         jwt_access_token, jwt_refresh_token, jti = await _generate_and_store_tokens(user.id)
#
#         _set_refresh_token_cookie(response, jwt_refresh_token)
#
#         return KakaoOauthResponse(
#             access_token=jwt_access_token,
#             id=user.id,
#             profile_image_url=user.image_url,
#         )
#     except Exception as e:
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="데이터베이스 연결 오류입니다.")
#
#
# async def _generate_and_store_tokens(user_id: int) -> tuple[str, str, str]:
#
#     jwt_access_token = create_jwt_token({"id": user_id, "type": "access"}, expires_delta=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
#
#     jwt_refresh_token = create_jwt_token({"id": user_id, "type": "refresh"}, expires_delta=settings.REFRESH_TOKEN_EXPIRE_DAYS)
#     jti = decode_jwt_token(jwt_refresh_token).get("jti")
#
#     try:
#         await save_refresh_token(user_id, jti)
#     except RedisError:
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Redis 저장 오류")
#
#     return jwt_access_token, jwt_refresh_token, jti
#
#
# def _set_refresh_token_cookie(response: Response, refresh_token: str):
#
#     response.set_cookie(
#         key="refresh_token",
#         value=refresh_token,
#         httponly=True,
#         secure=True,
#         max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
#         samesite="none",
#     )
