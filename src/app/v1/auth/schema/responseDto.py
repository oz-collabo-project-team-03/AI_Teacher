from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr


class TokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    access_token: str
    token_type: str
    expires_in: int
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
    email: str


class UserInfoResponse(BaseModel):
    email: EmailStr
    phone: str
    school: str | None  # 학생 전용
    grade: int | None  # 학생 전용 (GradeNumber)


class SocialLoginResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    access_token: str
    token_type: str
    expires_in: int
    role: str | None
    study_group: bool | None
    message: str

class StudentRoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    role: str
    first_login: bool
    study_group: bool
    message: str

class TeacherRoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    role: str
    first_login: bool
    message: str