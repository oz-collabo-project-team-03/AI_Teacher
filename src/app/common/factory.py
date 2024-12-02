from src.app.v1.chat.repository.room_repository import RoomRepository
from src.app.v1.chat.service.chat import ChatService
from src.app.v1.chat.service.room_service import RoomService
from src.config.database.mongo import mongodb


def get_room_service() -> RoomService:
    room_repository = RoomRepository()
    return RoomService(room_repository)


def get_chat_service() -> ChatService:
    room_repository = RoomRepository()
    return ChatService()


async def mongo_db():
    async for db in mongodb.get_db():
        yield db
