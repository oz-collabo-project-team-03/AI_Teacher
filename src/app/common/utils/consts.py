from enum import Enum

from pydantic import BaseModel


class UserRole(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"


class User(BaseModel):
    role: UserRole = UserRole.STUDENT


user = User(role=UserRole.STUDENT)
user = User(role=UserRole.TEACHER)


class SocialProvider(str, Enum):
    GOOGLE = "google"
    NAVER = "naver"
    KAKAO = "kakao"


class Visibility(Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    TEACHER = "teacher"
    STUDENT = "student"


class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
