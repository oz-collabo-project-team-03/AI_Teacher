from typing import Optional

from pydantic import BaseModel, Field


class PostCreateRequest(BaseModel):
    content: str = Field(..., max_length=300)
    image1: str
    image2: Optional[str] = None
    image3: Optional[str] = None
    is_with_teacher: bool = False


class PostUpdateRequest(BaseModel):
    content: Optional[str] = Field(None, max_length=300)
    image1: Optional[str] = None
    image2: Optional[str] = None
    image3: Optional[str] = None
    is_with_teacher: Optional[bool] = False


class PostDeleteRequest(BaseModel):
    post_id: str


class PostGetResponse(BaseModel):
    user_id: str
    profile_image: str
    career_aspiration: Optional[str] = None
    interest: Optional[str] = None
    image1: str
    image2: Optional[str] = None
    image3: Optional[str] = None
