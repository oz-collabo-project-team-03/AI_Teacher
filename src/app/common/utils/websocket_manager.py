import logging
import os
from dotenv import load_dotenv
from sqlalchemy.future import select
from datetime import datetime
from src.app.common.utils.consts import UserRole
from fastapi import WebSocket, HTTPException
from aiokafka import AIOKafkaProducer
from src.app.v1.chat.repository.room_repository import RoomRepository
from src.config.database.postgresql import SessionLocal
from src.app.v1.chat.entity.room import Room
from src.app.v1.chat.entity.message import Message
from src.config.database.mongo import MongoDB

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mongo = MongoDB()


load_dotenv()


class ConnectionManager:

    # def __init__(self, mongo: AIOEngine = Depends(mongo_db)):mongodb
    def __init__(self):
        self.active_connections: dict[int, dict[int, WebSocket]] = {}  # room_id: {user_id: websocket}
        self.mongo = mongo
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.ai_user_id = 0
        self.ai_welcome_message = "AI 선생님과의 대화가 시작되었습니다. 궁금한 점을 물어보세요!"
        self.producer = None
        self.chat_topic = os.environ.get("CHAT_TOPIC")

    async def initialize(self, producer: AIOKafkaProducer):
        """Initialize the Kafka producer"""
        self.producer = producer
        logger.info("Kafka producer initialized")

    async def connect(self, websocket: WebSocket, room_id: int, user_id: int, user_type: UserRole):
        await websocket.accept()

        if room_id not in self.active_connections:
            self.active_connections[room_id] = {}

        room = await RoomRepository.room_exists(room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")

        self.active_connections[room_id][user_id] = websocket

        if user_type == UserRole.STUDENT and not self.active_connections[room_id].get(user_id):
            welcome_message = {
                "room_id": room_id,
                "sender_id": os.getenv("AI_USER_ID"),
                "content": self.ai_welcome_message,
                "timestamp": datetime.now().isoformat(),
            }
            await self.send_message(welcome_message)

    async def disconnect(self, room_id: int, user_id: int):
        if room_id in self.active_connections:
            self.active_connections[room_id].pop(user_id, None)
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]

    async def toggle_help_state(self, room_id: int) -> bool:
        async with SessionLocal() as session:
            try:
                query = select(Room).where(Room.id == room_id)
                result = await session.execute(query)
                room = result.scalar_one_or_none()

                if room is None:
                    logger.warning(f"Room ID: {room_id}가 존재하지 않습니다.")
                    return False

                # help_checked 속성의 값을 반전시키는 작업
                room.help_checked = not room.help_checked
                room.updated_at = datetime.now()

                await session.commit()

                message = {
                    "type": "system",
                    "room_id": room_id,
                    "user_id": "SYSTEM",
                    "content": "선생님과의 대화가 시작되었습니다." if room.help_checked else "AI 선생님과의 대화가 다시 시작되었습니다.",
                    "timestamp": datetime.now().isoformat(),
                }
                logger.info(f"Send Message {message}")
                await self.send_message(message)

                return room.help_checked

            except Exception as e:
                logger.error(f"Error toggling help state for Room ID {room_id}: {str(e)}")
                await session.rollback()
                return False

    async def can_send_message(self, room_id: int, user_type: UserRole) -> bool:
        async with SessionLocal() as session:
            try:
                query = select(Room).where(Room.id == room_id)
                result = await session.execute(query)
                room = result.scalar_one_or_none()

                if not room:
                    return False

                if user_type == UserRole.STUDENT:
                    return True
                elif user_type == UserRole.TEACHER:
                    return room.help_checked
                return False

            except Exception as e:
                logger.error(f"Error checking message permission for Room ID {room_id}: {str(e)}")
                return False

    async def ai_chat(self, message: str):
        try:
            print("완성되지 않은 AI")
            # response = await openai.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": message}])
            # return response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI API Error: {e}")
            return "죄송합니다. 현재 AI 응답을 생성할 수 없습니다."

    async def send_message(self, message: dict):
        """Kafka에 메시지를 전송하고 웹소켓으로 브로드캐스트합니다."""
        if self.producer:
            try:
                await self.producer.send_and_wait(self.chat_topic, message)
                logger.info("Kafka producer initialized")
            except Exception as e:
                logger.error(f"Failed to send message to Kafka: {e}")
        else:
            logger.warning("Kafka producer not initialized")
        return await self.broadcast_message(message)

    async def broadcast_message(self, message: dict):
        """웹소켓 연결된 클라이언트들에게 메시지를 전송합니다."""
        room_id = message["room_id"]
        if room_id in self.active_connections:
            message_model = Message(**message)

            engine = await mongo.get_engine()
            if engine:
                await engine.save(message_model)
            for websocket in self.active_connections[room_id].values():
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    print(f"Failed to send message to websocket: {e}")

    async def handle_kafka_message(self, message: dict):
        """Kafka 메시지를 처리하고 웹소켓으로 브로드캐스트합니다."""
        await self.broadcast_message(message)


manager = ConnectionManager()
