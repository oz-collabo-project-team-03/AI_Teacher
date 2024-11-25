import os
import pytest
from sqlalchemy.engine import URL
from sqlalchemy.future import select
from src.app.v1.user.entity.user import User  # 실제 모듈 경로로 변경하세요
from src.app.common.utils.consts import UserRole
from sqlalchemy.ext.asyncio import AsyncSession
from src.config.database import SessionLocal


def test_database_url_creation():
    """환경 변수로부터 데이터베이스 URL이 올바르게 생성되는지 테스트합니다."""
    from dotenv import load_dotenv

    load_dotenv()

    user = os.environ.get("DB_USER")
    password = os.environ.get("DB_PASSWORD")
    host = os.environ.get("DB_HOST")
    database = os.environ.get("DB_NAME")
    port = int(os.environ.get("DB_PORT", "5432"))

    expected_url = URL.create(
        drivername="postgresql+asyncpg",
        username=user,
        password=password,
        host=host,
        port=port,
        database=database,
    )

    assert expected_url is not None
    assert expected_url.drivername == "postgresql+asyncpg"
    assert expected_url.username == "test"
    assert expected_url.password == "test!!!"
    assert expected_url.host == "test"
    assert expected_url.port == 5432
    assert expected_url.database == "test"
