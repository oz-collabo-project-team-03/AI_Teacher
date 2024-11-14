from datetime import datetime

import os

from dotenv import load_dotenv

import pytest
import asyncio
import asyncpg
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from src.app.common.utils.consts import SocialProvider, UserRole
from src.app.v1.user.entity.user import User
from src.config.database import Base

load_dotenv()

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


@pytest.fixture(scope="function")
async def fake_db():
    if TEST_DATABASE_URL is None:
        raise ValueError("TEST_DATABASE_URL environment variable is not set")

    conn = await asyncpg.connect(TEST_DATABASE_URL)

    # 테이블 생성
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            external_id TEXT,
            email TEXT UNIQUE,
            phone TEXT,
            password TEXT,
            profile_image TEXT,
            social_provider TEXT,
            role TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    yield conn

    # 테스트 후 테이블 삭제 및 연결 종료
    await conn.execute("DROP TABLE IF EXISTS users")
    await conn.close()


@pytest.mark.asyncio
async def test_create_user(fake_db):
    async with fake_db.transaction():
        user = {
            "id": 1,
            "external_id": "1234",
            "email": "test@example.com",
            "phone": "01012345678",
            "password": "password",
            "profile_image": "http://example.com/image.png",
            "social_provider": SocialProvider.GOOGLE.value,
            "role": UserRole.student.value,
            "is_active": True,
        }

    async with fake_db.transaction():  # 이제 fake_db는 실제 연결 객체입니다.
        await fake_db.execute(
            """
            INSERT INTO users (id, external_id, email, phone, password, profile_image, social_provider, role, is_active)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
            *user.values()
        )

        retrieved_user = await fake_db.fetchrow("SELECT * FROM users WHERE email = $1", "test@example.com")
        assert retrieved_user is not None
        assert retrieved_user["email"] == "test@example.com"
        assert retrieved_user["is_active"] is True
        assert retrieved_user["created_at"] is not None
        assert retrieved_user["updated_at"] is not None


@pytest.mark.asyncio
async def test_unique_email(fake_db):
    async with fake_db.transaction():
        user1 = {
            "id": 2,
            "external_id": "12345",
            "email": "unique@example.com",
            "password": "password1",
            "social_provider": SocialProvider.GOOGLE.value,
            "role": UserRole.teacher.value,
        }

        await fake_db.execute(
            """
            INSERT INTO users (id, external_id, email, password, social_provider, role)
            VALUES ($1, $2, $3, $4, $5, $6)
        """,
            *user1.values()
        )

        user2 = {
            "id": 3,
            "external_id": "12346",
            "email": "unique@example.com",
            "password": "password2",
            "social_provider": SocialProvider.NAVER.value,
            "role": UserRole.student.value,
        }

        with pytest.raises(asyncpg.UniqueViolationError):
            await fake_db.execute(
                """
                INSERT INTO users (id, external_id, email, password, social_provider, role)
                VALUES ($1, $2, $3, $4, $5, $6)
            """,
                *user2.values()
            )


@pytest.mark.asyncio
async def test_defaults(fake_db):
    async with fake_db.transaction():
        user = {
            "id": 4,
            "external_id": "12347",
            "email": "default@example.com",
            "password": "password",
            "social_provider": SocialProvider.KAKAO.value,
            "role": UserRole.teacher.value,
        }

        await fake_db.execute(
            """
            INSERT INTO users (id, external_id, email, password, social_provider, role)
            VALUES ($1, $2, $3, $4, $5, $6)
        """,
            *user.values()
        )

        retrieved_user = await fake_db.fetchrow("SELECT * FROM users WHERE email = $1", "default@example.com")
        assert retrieved_user["is_active"] is True
        assert isinstance(retrieved_user["created_at"], datetime)
        assert isinstance(retrieved_user["updated_at"], datetime)
