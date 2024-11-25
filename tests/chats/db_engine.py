import os
import pytest
from sqlalchemy.engine import URL
from sqlalchemy.future import select
from src.app.v1.user.entity.user import User  # 실제 모듈 경로로 변경하세요
from src.app.common.utils.consts import UserRole
from sqlalchemy.ext.asyncio import AsyncSession
from src.config.database import SessionLocal


@pytest.fixture(scope="module", autouse=True)
def setup_env():
    """환경 변수를 설정합니다."""
    os.environ["DB_USER"] = "ozcoding"
    os.environ["DB_PASSWORD"] = "qwe123!!!"
    os.environ["DB_HOST"] = "pg-2vt4js.vpc-pub-cdb-kr.ntruss.com"
    os.environ["DB_NAME"] = "sam"
    os.environ["DB_PORT"] = "5432"


@pytest.fixture(scope="function")
async def db_session():
    """데이터베이스 세션을 제공하는 fixture"""
    async with SessionLocal() as session:
        yield session
        await session.rollback()


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
    assert expected_url.username == "ozcoding"
    assert expected_url.password == "qwe123!!!"
    assert expected_url.host == "pg-2vt4js.vpc-pub-cdb-kr.ntruss.com"
    assert expected_url.port == 5432
    assert expected_url.database == "sam"
