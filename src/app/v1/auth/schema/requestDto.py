from pydantic import BaseModel, ConfigDict, EmailStr, Field

from src.app.common.utils.consts import UserRole


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


class CurrentUser(BaseModel):
    access_token: str
    user_id: int
    role: UserRole


class PhoneRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    phone: str


class UpdatePasswordRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    password: str = Field(..., min_length=10, max_length=20, description="10~20자리의 영문+숫자 조합")


class UpdateUserInfoRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    email: EmailStr | None
    password: str | None = Field(None, min_length=10, max_length=20, description="10~20자리의 영문+숫자 조합")


class KakaoCallbackRequest(BaseModel):
    code: str


class SocialStudentRegisterRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    role: UserRole = UserRole.STUDENT
    phone: str
    is_privacy_accepted: bool
    school: str
    grade: int
    career_aspiration: str | None
    interests: str | None


class SocialTeacherRegisterRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    role: UserRole = UserRole.TEACHER
    phone: str
    is_privacy_accepted: bool
    organization_name: str
    organization_type: str
    position: str


class AdditionalInfoRequest(BaseModel):
    external_id: str
    phone: str
    is_privacy_accepted: bool
    role: str
    school: str | None = None
    grade: int | None = None
    career_aspiration: str | None = None
    interests: str | None = None
    organization_name: str | None = None
    organization_type: str | None = None
    position: str | None = None


class EmailRequest(BaseModel):
    email: str


class EmailVerifyRequest(BaseModel):
    email: str
    code: str
    encrypted_code: str
    expiry_time: float


# class SocialLoginBaseRegisterRequest(BaseModel):
#     email: EmailStr
#     phone: str


class SocialLoginStudentRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    role: UserRole = UserRole.STUDENT
    nickname: str
    is_privacy_accepted: bool
    school: str
    grade: int
    career_aspiration: str | None
    interests: str | None


class SocialLoginTeacherRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    role: UserRole = UserRole.TEACHER
    nickname: str
    is_privacy_accepted: bool
    organization_name: str
    organization_type: str
    position: str


class OAuthRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    code: str
