import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
import random
import string
from datetime import datetime
from argon2 import PasswordHasher
from src.app.common.models.tag import Tag
from src.app.v1.user.entity.organization import Organization
from src.app.v1.user.entity.teacher import Teacher
from src.app.v1.user.entity.user import User
from src.config.database.postgresql import DATABASE_URL, engine, SessionLocal, Base

# 모델 정의를 여기다가

# 미리 정의된 비밀번호 패턴
PASSWORD_PATTERNS = [
    "qwer1234!!",
    "asdf1234!!",
    "qwe123!!!!",
    "asdfqwer1!",
    "ozozoz11!!",
    "oooooooo1!",
    "aaaaaaaa1!",
    "qwerqwer1!",
    "asdfasdf1!",
    "zxcvzxcv1!"
]

# 학교 및 학원 데이터 정의
ORGANIZATION_TYPES = ["학교", "학원"]
SCHOOL_NAMES = ["오즈중학교", "오즈고등학교"]
ACADEMY_NAMES = ["스터디에듀", "메가스터디"]

# 중복 데이터 방지
generated_emails = set()
generated_phones = set()
generated_nicknames = set()

# 한글 이름 생성
def generate_korean_name():
    first = ["김", "박", "이", "최", "정", "강", "조", "윤", "장", "임"]
    middle = ["민", "서", "수", "현", "영", "진", "아", "은", "우", "준"]
    last = ["희", "재", "지", "원", "연", "호", "훈", "혁", "슬", "율"]
    return random.choice(first) + random.choice(middle) + random.choice(last)

# 비밀번호 선택
def select_password() -> str:
    return random.choice(PASSWORD_PATTERNS)

# Argon2 해싱
def hash_password(password: str) -> str:
    ph = PasswordHasher()
    return ph.hash(password)

# 랜덤 문자열 생성
def random_string(length: int) -> str:
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

# 중복되지 않는 이메일 생성
def generate_unique_email():
    while True:
        email = f"{random_string(5)}@example.com"
        if email not in generated_emails:
            generated_emails.add(email)
            return email

# 중복되지 않는 핸드폰 번호 생성
def generate_unique_phone():
    while True:
        phone = f"+8210{random.randint(10000000, 99999999)}"
        if phone not in generated_phones:
            generated_phones.add(phone)
            return phone

# 중복되지 않는 닉네임 생성
def generate_unique_nickname():
    while True:
        nickname = generate_korean_name()
        if nickname not in generated_nicknames:
            generated_nicknames.add(nickname)
            return nickname

# Teacher 데이터 생성 제너레이터
async def generate_teacher_data(num_teachers: int = 5):
    for _ in range(num_teachers):
        plain_password = select_password()

        # User 데이터 생성
        user_data = {
            "external_id": random_string(10),
            "email": f"{random_string(5)}@example.com",
            "phone": f"+8210{random.randint(10000000, 99999999)}",
            "password": hash_password(plain_password),  # Argon2 해싱된 비밀번호
            "profile_image": None,
            "social_provider": None,
            "first_login": False,  # 선생님은 무조건 False
            "role": "teacher",  # UserRole Enum 값
            "is_active": True,
            "is_privacy_accepted": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        # Organization 데이터 생성
        organization_type = random.choice(ORGANIZATION_TYPES)
        if organization_type == "학교":
            organization_name = random.choice(SCHOOL_NAMES)
            position = "교사"
        else:
            organization_name = random.choice(ACADEMY_NAMES)
            position = "강사"

        teacher_data = {
            "organization_type": organization_type,
            "organization_name": organization_name,
            "position": position,
        }

        # Tag 데이터 생성
        tag_data = {
            "tag_nickname": generate_korean_name()
        }

        yield {
            "user": user_data,
            "teacher": teacher_data,
            "tag": tag_data,
        }



# 데이터 삽입 함수
async def insert_teachers_async(session: AsyncSession, num_teachers: int = 5):
    async for teacher_data in generate_teacher_data(num_teachers):
        try:
            # User 객체 생성
            user = User(**teacher_data["user"])
            session.add(user)
            await session.flush()

            # Organization 객체 생성
            organization = Organization(
                name=teacher_data["teacher"]["organization_name"],
                type=teacher_data["teacher"]["organization_type"],
                position=teacher_data["teacher"]["position"],
                teacher_id=user.id
            )
            session.add(organization)

            # Tag 객체 생성
            tag = Tag(
                nickname=teacher_data["tag"]["tag_nickname"],
                user_id=user.id
            )
            session.add(tag)

            # Teacher 객체 생성
            teacher = Teacher(user_id=user.id)
            session.add(teacher)

        except Exception as e:
            print(f"데이터 삽입 중 오류 발생: {e}")
            await session.rollback()
            raise

    await session.commit()
    print(f"{num_teachers}명의 교사 데이터가 성공적으로 생성되었습니다.")

