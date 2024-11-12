from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.environ.get("PG_DATABASE_URL")
engine = create_async_engine(DATABASE_URL, echo=True)

SessionLocal = async_sessionmaker(
    engine=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # 트랜잭션 커밋 후에도 객체가 만료되지 않는 설정 값
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()  # 모델 정의 시 상속 받아서 사용
