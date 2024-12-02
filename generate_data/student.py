import asyncio
import random
import string
from datetime import datetime
from argon2 import PasswordHasher
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from src.app.common.models.tag import Tag
from src.app.v1.user.entity.user import User
from src.app.v1.user.entity.student import Student
from src.config.database import SessionLocal
from src.config.database.postgresql import engine, Base

# 순서 기반 인덱스
email_counter = 0
phone_counter = 10000000
nickname_counter = 0


# 랜덤 문자열 생성
def random_string(length: int) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


# 알파벳 순서로 이메일 생성
def generate_ordered_email():
    global email_counter
    alphabet = string.ascii_lowercase
    base = email_counter % (len(alphabet) ** 4)
    email = "".join(alphabet[base // len(alphabet) ** i % len(alphabet)] for i in reversed(range(4)))
    email_counter += 1
    return f"{email}@example.com"


# 순차적으로 전화번호 생성
def generate_ordered_phone():
    global phone_counter
    phone = f"010{phone_counter}"
    phone_counter += 1
    return phone


# 닉네임 생성
def generate_ordered_nickname():
    global nickname_counter
    adjectives = ["귀여운", "용감한", "빠른", "느긋한", "똑똑한", "멋진", "활기찬", "침착한", "웃긴", "배고픈", "잠이 많은", "행복한", "슬픈", "화난"]
    animals = [
        "고양이",
        "강아지",
        "호랑이",
        "사자",
        "코끼리",
        "펭귄",
        "토끼",
        "다람쥐",
        "여우",
        "늑대",
        "돌고래",
        "원숭이",
        "햄스터",
        "공작",
        "독수리",
    ]
    nickname = f"{adjectives[nickname_counter % len(adjectives)]} {animals[nickname_counter % len(animals)]}"
    nickname_counter += 1
    return nickname


# 비밀번호 선택
PASSWORD_PATTERNS = [
    "qwe123!@#",
]


def select_password() -> str:
    return random.choice(PASSWORD_PATTERNS)


def hash_password(password: str) -> str:
    ph = PasswordHasher()
    return ph.hash(password)


# 학생 데이터 생성 제너레이터
async def generate_student_data(num_students: int = 50):
    SCHOOLS = ["오즈중학교", "오즈고등학교", "수행중학교", "수행고등학교", "파이중학교", "파이고등학교"]
    CAREER_OPTIONS = ["의사", "개발자", "선생님", "연구원", "경영자", "대통령", "요리사", "교사", "치과의사", "코인부자", "부자"]
    INTERESTS = ["음악", "운동", "독서", "코딩", "미술", "노래부르기", "음악감상", "스키타기", "등산", "수다떨기", "취미없음"]

    for _ in range(num_students):
        # User 데이터 생성
        plain_password = select_password()
        user_data = {
            "external_id": random_string(10),
            "email": generate_ordered_email(),
            "phone": generate_ordered_phone(),
            "password": hash_password(plain_password),
            "profile_image": None,
            "social_provider": None,
            "first_login": False,
            "role": "student",  # 학생
            "is_active": True,
            "is_privacy_accepted": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        # Student 데이터 생성
        student_data = {
            "school": random.choice(SCHOOLS),
            "grade": random.randint(1, 3),  # 중학교/고등학교 학년
            "career_aspiration": random.choice(CAREER_OPTIONS) if random.random() > 0.5 else None,
            "interest": random.choice(INTERESTS) if random.random() > 0.5 else None,
            "description": f"{random.choice(CAREER_OPTIONS)}를 꿈꾸는 학생" if random.random() > 0.5 else None,
        }

        # Tag 데이터 생성
        tag_data = {"tag_nickname": generate_ordered_nickname()}

        yield {
            "user": user_data,
            "student": student_data,
            "tag": tag_data,
        }


# 데이터 삽입 함수
async def insert_students_async(session: AsyncSession, num_students: int = 50):
    async for student_data in generate_student_data(num_students):
        try:
            # User 객체 생성
            user = User(**student_data["user"])
            session.add(user)
            await session.flush()  # User ID 확보

            # Student 객체 생성
            student = Student(
                school=student_data["student"]["school"],
                grade=student_data["student"]["grade"],
                career_aspiration=student_data["student"]["career_aspiration"],
                interest=student_data["student"]["interest"],
                description=student_data["student"]["description"],
                user_id=user.id,
            )
            session.add(student)

            # Tag 객체 생성
            tag = Tag(nickname=student_data["tag"]["tag_nickname"], user_id=user.id)
            session.add(tag)

        except Exception as e:
            print(f"데이터 삽입 중 오류 발생: {e}")
            await session.rollback()
            raise

    try:
        await session.commit()
        print(f"{num_students}명의 학생 데이터를 생성했습니다.")
    except Exception as e:
        print(f"커밋 중 오류 발생: {e}")
        await session.rollback()
        raise
