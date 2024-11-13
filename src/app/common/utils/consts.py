from enum import Enum as PyEnum

class UserRole(PyEnum):
    student = 'student'
    teacher = 'teacher'

class SocialProvider(PyEnum):
    GOOGLE = 'google'
    NAVER = 'naver'
    KAKAO = 'kakao'