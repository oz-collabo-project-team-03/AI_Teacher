import os

import pytest
import sqlalchemy
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture(scope="module")
def database_url():
    load_dotenv()

    user = os.environ.get("DB_USER")
    password = os.environ.get("DB_PASSWORD")
    host = os.environ.get("DB_HOST")
    database = os.environ.get("DB_NAME")
    port = int(os.environ.get("DB_PORT", "5432"))

    database_url = sqlalchemy.engine.URL.create(
        drivername="postgresql+asyncpg",
        username=user,
        password=password,
        host=host,
        port=port,
        database=database,
    )
    return database_url


@pytest.mark.asyncio
async def test_database_connection(database_url):
    engine = create_async_engine(database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            # 간단한 쿼리 실행
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1
        print("Database connection successful")
    except SQLAlchemyError as e:
        pytest.fail(f"Database connection failed: {str(e)}")
    finally:
        await engine.dispose()
