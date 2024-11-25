import os
import sqlalchemy

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

load_dotenv()

user = os.environ.get("DB_USER")
password = os.environ.get("DB_PASSWORD")
host = os.environ.get("DB_HOST")
database = os.environ.get("DB_NAME")
port = int(os.environ.get("DB_PORT", "5432"))

DATABASE_URL = sqlalchemy.engine.URL.create(
    drivername="postgresql+asyncpg",
    username=user,
    password=password,
    host=host,
    port=port,
    database=database,
)


# DATABASE_URL이 None인 경우 처리
if DATABASE_URL is None:
    raise ValueError("PG_DATABASE_URL environment variable is not set")

engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    connect_args={"server_settings": {"timezone": "Asia/Seoul"}},
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # 트랜잭션 커밋 후에도 객체가 만료되지 않는 설정 값
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()  # 모델 정의 시 상속 받아서 사용
