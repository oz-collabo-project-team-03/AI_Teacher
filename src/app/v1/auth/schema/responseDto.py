from typing import Optional

from pydantic import BaseModel


class KakaoOauthResponse(BaseModel):
    access_token: str
    id: int
    profile_image_url: str | None


class KakaoOauthErrorResponse(BaseModel):
    error: str
    detail: str | None
