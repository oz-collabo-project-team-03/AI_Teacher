from pydantic import BaseModel, ConfigDict, EmailStr


class TokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    access_token: str
    refresh_token: str
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
    grade: str | None  # 학생 전용 (GradeNumber)


from typing import Literal
