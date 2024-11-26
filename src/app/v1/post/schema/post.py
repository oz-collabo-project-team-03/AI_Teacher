from typing import Optional

from pydantic import BaseModel, Field


class PostCreateRequest(BaseModel):
    content: str = Field(..., max_length=300)
    image1: str | None = None
    image2: str | None = None
    image3: str | None = None
    is_with_teacher: bool = False


class PostUpdateRequest(BaseModel):
    content: str | None = Field(None, max_length=300)
    image1: str | None = None
    image2: str | None = None
    image3: str | None = None
    is_with_teacher: Optional[bool] = False


class PostDeleteRequest(BaseModel):
    post_id: str


class LikeRequest(BaseModel):
    like: bool


class PostGetResponse(BaseModel):
    user_id: str
    profile_image: str
    career_aspiration: str | None = None
    interest: str | None = None
    image1: str
    image2: str | None = None
    image3: str | None = None
