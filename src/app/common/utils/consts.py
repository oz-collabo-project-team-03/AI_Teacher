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


class GradeNumber(PyEnum):
    FIRST_GRADE = "1학년"
    SECOND_GRADE = "2학년"
    THIRD_GRADE = "3학년"
