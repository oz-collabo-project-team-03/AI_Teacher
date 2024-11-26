# import os
#
# import requests
# from dotenv import load_dotenv
# from fastapi import HTTPException
#
# load_dotenv()
#
#
# class KakaoService:
#     def __init__(self):
#         self.client_id = os.getenv("KAKAO_CLIENT_ID")
#         self.client_secret = os.getenv("KAKAO_CLIENT_SECRET")
#         self.redirect_uri = os.getenv("KAKAO_REDIRECT_URI")
#         self.token_url = "https://kauth.kakao.com/oauth/token"
#         self.user_info_url = "https://kapi.kakao.com/v2/user/me"
#         self.auth_url = "https://kauth.kakao.com/oauth/authorize"
#
#     # Kakao OAuth 인증 URL 생성
#     def get_auth_url(self) -> str:
#
#         return f"{self.auth_url}" f"?response_type=code" f"&client_id={self.client_id}" f"&redirect_uri={self.redirect_uri}"
#
#     # Kakao 인가 코드 ->  Access Token 및 Refresh Token 교환
#     def exchange_token(self, code: str) -> dict:
#         data = {
#             "grant_type": "authorization_code",
#             "client_id": self.client_id,
#             "client_secret": self.client_secret,
#             "redirect_uri": self.redirect_uri,
#             "code": code,
#         }
#         response = requests.post(self.token_url, data=data)
#
#         if response.status_code != 200:
#             raise HTTPException(status_code=400, detail="Failed to fetch access token from Kakao")
#
#         return response.json()
#
#     # Access Token을 사용해 kakao에서 사용자 정보 가져오기
#     def get_kakao_user_info(self, access_token: str) -> dict:
#
#         headers = {"Authorization": f"Bearer {access_token}"}
#         response = requests.get(self.user_info_url, headers=headers)
#
#         if response.status_code != 200:
#             raise HTTPException(status_code=400, detail="Failed to fetch user info from Kakao")
#
#         return response.json()
