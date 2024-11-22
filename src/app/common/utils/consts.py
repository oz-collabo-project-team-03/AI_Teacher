from enum import Enum

from pydantic import BaseModel


class UserRole(Enum):
    STUDENT = "student"
    TEACHER = "teacher"


class User(BaseModel):
    role: UserRole


user = User(role=UserRole.STUDENT)
user = User(role=UserRole.TEACHER)


class SocialProvider(Enum):
    GOOGLE = "google"
    NAVER = "naver"
    KAKAO = "kakao"


class Visibility(Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    TEACHER = "teacher"
    STUDENT = "student"


class GradeNumber(Enum):
    FIRST_GRADE = "1"
    SECOND_GRADE = "2"
    THIRD_GRADE = "3"


class MessageType(Enum):
    TEXT = "text"
    IMAGE = "image"
