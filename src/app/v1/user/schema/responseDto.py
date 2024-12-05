from typing import List, Union

from pydantic import BaseModel, ConfigDict, EmailStr

from src.app.common.utils.consts import UserRole


class TokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    access_token: str
    refresh_token: str  # 테스트 용
    token_type: str
    expires_in: int
    role: str
    first_login: bool
    message: str


class AccessTokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    access_token: str
    token_type: str
    expires_in: int
    message: str


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    message: str


class EmailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    email: EmailStr


class TempPasswordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    message: str
    email: EmailStr
    temp_password: str


class UserInfoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    email: EmailStr
    phone: str
    school: str | None  # 학생 전용
    grade: str | None  # 학생 전용 (GradeNumber)


class CommonProfileResponse(BaseModel):
    role: str
    id: int
    nickname: str
    profile_image: str | None
    post_count: int
    like_count: int
    comment_count: int


class PostResponse(BaseModel):
    post_id: str
    post_image: str | None


class StudentProfileResponse(CommonProfileResponse):
    school: str
    grade: str
    career_aspiration: str | None
    interest: str | None
    description: str | None
    posts: List[PostResponse]


class TeacherProfileResponse(CommonProfileResponse):
    organization_name: str
    organization_type: str
    position: str
    posts: List[PostResponse]


class CurrentUser(BaseModel):
    access_token: str
    user_id: int
    role: str


class TeachersResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    teacher_id: int
    name: str
    organization_name: str
    organization_type: str
    position: str
