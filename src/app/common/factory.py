from src.app.v1.chat.repository.room_repository import RoomRepository
from src.app.v1.chat.service.room_service import RoomService

from src.config.database.mongo import mongodb

def get_room_service() -> RoomService:
    room_repository = RoomRepository()
    return RoomService(room_repository)


async def mongo_db():
    async for db in mongodb.get_db():
        yield db
