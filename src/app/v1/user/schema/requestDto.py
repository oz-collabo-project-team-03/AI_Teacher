from pydantic import BaseModel, ConfigDict, EmailStr, Field

from src.app.common.utils.consts import UserRole


class EmailRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    email: EmailStr


class EmailVerifyRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    email: EmailStr
    code: str


class StudentRegisterRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    email: EmailStr
    password: str = Field(..., min_length=10, max_length=20)
    password_confirm: str
    nickname: str
    phone: str
    is_privacy_accepted: bool
    role: UserRole = UserRole.STUDENT
    school: str
    grade: int
    career_aspiration: str | None
    interests: str | None


class TeacherRegisterRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    email: EmailStr
    password: str = Field(..., min_length=10, max_length=20)
    password_confirm: str
    nickname: str
    phone: str
    is_privacy_accepted: bool
    role: UserRole = UserRole.TEACHER
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
    password: str = Field(..., min_length=10, max_length=20, description="10~20자리의 영문+숫자 조합")


class UpdateUserInfoRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    email: EmailStr | None
    password: str | None = Field(None, min_length=10, max_length=20, description="10~20자리의 영문+숫자 조합")

    class EmailRequest(BaseModel):
        model_config = ConfigDict(from_attributes=True)
        email: EmailStr

    class EmailVerifyRequest(BaseModel):
        model_config = ConfigDict(from_attributes=True)
        email: EmailStr
        code: str

    class StudentRegisterRequest(BaseModel):
        model_config = ConfigDict(from_attributes=True)
        email: EmailStr
        password: str = Field(..., min_length=10, max_length=20)
        password_confirm: str
        nickname: str
        phone: str
        is_privacy_accepted: bool
        role: UserRole = UserRole.STUDENT
        school: str
        grade: int
        career_aspiration: str | None
        interests: str | None

    class TeacherRegisterRequest(BaseModel):
        model_config = ConfigDict(from_attributes=True)
        email: EmailStr
        password: str = Field(..., min_length=10, max_length=20)
        password_confirm: str
        nickname: str
        phone: str
        is_privacy_accepted: bool
        role: UserRole = UserRole.TEACHER
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
        password: str = Field(..., min_length=10, max_length=20, description="10~20자리의 영문+숫자 조합")

    class UpdateUserInfoRequest(BaseModel):
        model_config = ConfigDict(from_attributes=True)
        email: EmailStr
        password: str = Field(None, min_length=10, max_length=20, description="10~20자리의 영문+숫자 조합")
        password_confirm: str
        phone: str
        school: str
        grade: int
