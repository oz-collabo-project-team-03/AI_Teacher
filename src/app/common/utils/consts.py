from enum import Enum as PyEnum


class UserRole(PyEnum):
    student = "student"
    teacher = "teacher"


class SocialProvider(PyEnum):
    GOOGLE = "google"
    NAVER = "naver"
    KAKAO = "kakao"


class Visibility(PyEnum):
    PUBLIC = "public"
    PRIVATE = "private"
    TEACHER = "teacher"
    STUDENT = "student"
