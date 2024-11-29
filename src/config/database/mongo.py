import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from odmantic import AIOEngine
from contextlib import asynccontextmanager


class MongoDB:
    def __init__(self):
        # .env 파일에서 환경 변수 로드
        load_dotenv()

        # 환경 변수에서 설정 값 가져오기
        self.mongo_url = os.getenv("MONGO_URL")
        self.mongo_db_name = os.getenv("MONGO_DB_NAME", "mongo")
        self.mongo_max_connections = int(os.getenv("MONGO_MAX_CONNECTIONS", 10))
        self.mongo_min_connections = int(os.getenv("MONGO_MIN_CONNECTIONS", 1))

        self.__client: AsyncIOMotorClient | None
        self.__engine: AIOEngine | None

    @property
    def client(self) -> AsyncIOMotorClient | None:
        return self.__client

    @property
    def engine(self) -> AIOEngine | None:
        return self.__engine

    async def connect(self):
        """
        Connect to MongoDB
        """
        self.__client = AsyncIOMotorClient(
            self.mongo_url,
            maxPoolSize=self.mongo_max_connections,
            minPoolSize=self.mongo_min_connections,
        )
        self.__engine: AIOEngine | None = AIOEngine(client=self.__client, database=self.mongo_db_name)

    async def close(self):
        """
        Close MongoDB Connection
        """
        if self.__client:
            self.__client.close()
            self.__client: AsyncIOMotorClient | None = None
            self.__engine: AIOEngine | None = None

    @asynccontextmanager
    async def get_mongodb(self):
        await self.connect()
        try:
            yield self.__engine
        finally:
            await self.close()

    async def get_db(self):
        async with self.get_mongodb() as db:
            yield db


# MongoDB 인스턴스 생성
mongodb = MongoDB()
