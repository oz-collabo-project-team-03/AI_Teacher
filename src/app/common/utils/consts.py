from enum import Enum


class UserRole(Enum):
    student = "student"
    teacher = "teacher"


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
    FIRST_GRADE = "1학년"
    SECOND_GRADE = "2학년"
    THIRD_GRADE = "3학년"


class MessageType(Enum):
    TEXT = "text"
    IMAGE = "image"
