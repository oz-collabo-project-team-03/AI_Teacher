# from fastapi import APIRouter, Response
# from fastapi.security import OAuth2PasswordBearer
#
# from src.app.v1.auth.schema.requestDto import KakaoOauthResponse
# from src.app.v1.auth.schema.responseDto import KakaoOauthErrorResponse
#
# router = APIRouter(prefix="/auth", tags=["sociallogin"])
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
#
#
# # 카카오 로그인
#
#
# @router.get(
#     "/login/kakao",
#     response_model=KakaoOauthResponse,
#     responses={
#         400: {"model": KakaoOauthErrorResponse},
#         500: {"description": "Internal Server Error"},
#     },
# )
# async def login_kakao(code: str, response: Response):
#
#     try:
#         return await login_kakao_service(code, response)
#     except HTTPException as e:
#         raise e
#     except Exception as ex:
#         raise HTTPException(status_code=500, detail=f"서버 오류가 발생했습니다: {str(ex)}")
#
#
# @router.post(
#     "/login/kakao/callback",
#     response_model=KakaoOauthResponse,
#     responses={
#         400: {"model": KakaoOauthErrorResponse},
#         500: {"description": "Internal Server Error"},
#     },
# )
# async def login_kakao_callback(code: str, response: Response):
#     try:
#         return await login_kakao_service(code, response)
#     except HTTPException as e:
#         raise e
#     except Exception as ex:
#         raise HTTPException(status_code=500, detail=f"서버 오류가 발생했습니다: {str(ex)}")
