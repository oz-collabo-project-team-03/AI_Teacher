from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from src.app.common.utils.consts import UserRole


class EmailRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    email: EmailStr


class EmailVerifyRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    email: EmailStr
    code: str


class BaseRegisterRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True, discriminator="role")  # type: ignore
    role: UserRole


class StudentRegisterRequest(BaseRegisterRequest):
    role: UserRole = UserRole.STUDENT
    email: str
    password: str
    password_confirm: str
    nickname: str
    phone: str
    is_privacy_accepted: bool
    school: str
    grade: int
    career_aspiration: str | None
    interests: str | None


class TeacherRegisterRequest(BaseRegisterRequest):
    role: UserRole = UserRole.TEACHER
    email: str
    password: str
    password_confirm: str
    nickname: str
    phone: str
    is_privacy_accepted: bool
    organization_name: str
    organization_type: str
    position: str


class LoginRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    email: EmailStr
    password: str


class PhoneRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    phone: str


class UpdatePasswordRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    email: EmailStr


class CheckingPasswordRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    password: str


class UpdateUserInfoRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    role: str
    password: str | None = None
    password_confirm: str | None = None
    phone: str | None = None
    school: str | None = None  # 학생 전용
    grade: int | None = None  # 학생 전


class StudyGroupRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    teacher_id: int
    name: str


class UpdateStudentProfileRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    nickname: str | None = None
    profile_image: str | None = None
    career_aspiration: str | None = None
    interest: str | None = None
    description: str | None = None


class UpdateTeacherProfileRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    nickname: str | None = None
    profile_image: str | None = None
    organization_name: str | None = None
    organization_type: str | None = None
<<<<<<< Updated upstream
    position: str | None = None

=======
    position: str | None = Field(None, alias="organization_position")
>>>>>>> Stashed changes
