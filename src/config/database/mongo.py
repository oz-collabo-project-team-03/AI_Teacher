from contextlib import asynccontextmanager
import os
from typing import AsyncGenerator, Optional
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from odmantic import AIOEngine


class MongoDB:
    def __init__(self):
        # .env 파일에서 환경 변수 로드
        load_dotenv()

        # 환경 변수에서 설정 값 가져오기
        self.mongo_url = os.getenv("MONGO_URL")
        self.mongo_db_name = os.getenv("MONGO_DB_NAME", "mongo")
        self.mongo_max_connections = int(os.getenv("MONGO_MAX_CONNECTIONS", 10))
        self.mongo_min_connections = int(os.getenv("MONGO_MIN_CONNECTIONS", 1))

        self.__client: AsyncIOMotorClient | None = None
        self.__engine: AIOEngine | None = None

    @property
    def client(self) -> AsyncIOMotorClient | None:
        return self.__client

    @property
    def engine(self) -> AIOEngine | None:
        return self.__engine

    async def connect(self):
        """MongoDB에 연결합니다."""
        if not self.__client:
            self.__client = AsyncIOMotorClient(
                self.mongo_url,
                maxPoolSize=self.mongo_max_connections,
                minPoolSize=self.mongo_min_connections,
            )
            self.__engine = AIOEngine(client=self.__client, database=self.mongo_db_name)

    async def close(self):
        """
        Close MongoDB Connection
        """
        if self.__client:
            self.__client.close()
            self.__client: AsyncIOMotorClient | None = None
            self.__engine: AIOEngine | None = None

    async def get_engine(self) -> AIOEngine | None:
        """현재 엔진을 반환하거나 새로운 연결을 생성합니다."""
        if not self.__engine:
            await self.connect()
        if not self.__engine:
            raise RuntimeError("Failed to establish MongoDB connection")
        return self.__engine

    async def get_db(self) -> AsyncGenerator[Optional[AIOEngine], None]:
        """FastAPI dependency injection을 위한 데이터베이스 엔진을 제공합니다."""
        engine = await self.get_engine()
        try:
            yield engine
        finally:
            pass  # 연결은 애플리케이션 종료 시에만 닫습니다

    @asynccontextmanager
    async def get_mongodb(self) -> AsyncGenerator[Optional[AIOEngine], None]:
        """컨텍스트 매니저를 통한 데이터베이스 연결을 제공합니다."""
        engine = await self.get_engine()
        try:
            yield engine
        finally:
            pass  # 연결은 애플리케이션 종료 시에만 닫습니다

    # async def get_db(self):
    #     async with self.get_mongodb() as db:
    #         yield db


# MongoDB 인스턴스 생성
mongodb = MongoDB()
