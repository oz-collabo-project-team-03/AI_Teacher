import logging
import os
import asyncio
import json
from dotenv import load_dotenv
from sqlalchemy.future import select
from datetime import datetime
from src.app.common.utils.consts import UserRole
from fastapi import WebSocket, HTTPException
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
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

    def __init__(self):
        self.active_connections: dict[int, dict[int, WebSocket]] = {}  # room_id: {user_id: websocket}
        self.mongo = mongo
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.ai_user_id = 0
        self.ai_welcome_message = "AI 선생님과의 대화가 시작되었습니다. 궁금한 점을 물어보세요!"
        self.producer: AIOKafkaProducer | None = None
        self.consumer: AIOKafkaConsumer | None = None
        self.chat_topic = os.environ.get("CHAT_TOPIC")
        self._consumer_task = None
        self._running = False

    async def initialize(self, producer: AIOKafkaProducer, consumer: AIOKafkaConsumer):
        """Initialize the Kafka producer and consumer"""
        self.producer = producer
        self.consumer = consumer  # 소비자 초기화
        self._running = True
        self._consumer_task = asyncio.create_task(self.consume_messages())
        logger.info("Kafka producer and consumer initialized")

    async def stop(self):
        """Stop the consumer task"""
        self._running = False
        if self._consumer_task:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass

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

    async def handle_message(self, room: Room, user_id: int, user_type: UserRole, content: str):

        # 선생과 학생 대화
        message = {
            "room_id": room.id,
            "title": room.title,
            "sender_id": user_id,
            "content": content,
            "message_type": "text",
            "user_type": user_type.value,
            "timestamp": datetime.now().isoformat(),
        }
        await self.send_message(message)

        if not room.help_checked and user_type == UserRole.STUDENT:
            # ai_response = await self.ai_chat(content)
            ai_message = {
                "room_id": room.id,
                "title": room.title,
                "sender_id": self.ai_user_id,
                "content": "AI_Message",
                "message_type": "text",
                "user_type": "ai",
                "timestamp": datetime.now().isoformat(),
            }
            await self.send_message(ai_message)

        # await self.send_message(message)

    async def disconnect(self, room_id: int, user_id: int):
        if room_id in self.active_connections:
            self.active_connections[room_id].pop(user_id, None)
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]

    async def can_send_message(self, room_id: int, user_type: UserRole) -> bool:
        async with SessionLocal() as session:
            try:
                query = select(Room).where(Room.id == room_id)
                result = await session.execute(query)
                room = result.scalar_one_or_none()

                if not room:
                    return False

                # Students can always send messages
                if user_type == UserRole.STUDENT:
                    return True
                # Teachers can only send messages in teacher mode (help_checked=True)
                elif user_type == UserRole.TEACHER:
                    if not room.help_checked:
                        logger.info("Teacher attempted to send message in AI mode")
                        return False
                    return True

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

    # async def send_message(self, message: dict):
    #     """Kafka에 메시지를 전송하고 웹소켓으로 브로드캐스트합니다."""
    #     if self.producer:
    #         try:
    #             # Ensure message is JSON serializable
    #             json_message = json.loads(json.dumps(message))
    #             await self.producer.send_and_wait(self.chat_topic, value=json_message)
    #             logger.info(f"Message sent to Kafka: {message}")
    #         except Exception as e:
    #             logger.error(f"Failed to send message to Kafka: {e}")
    #     else:
    #         logger.warning("Kafka producer not initialized")

    async def send_message(self, message: dict):
        """Kafka에 메시지를 전송하고 웹소켓으로 브로드캐스트합니다."""
        if self.producer:
            try:
                # 메시지 전송 전 로깅
                logger.info(f"Sending message to Kafka: {message}")

                await self.producer.send_and_wait(self.chat_topic, json.dumps(message).encode("utf-8"))
                # await self.producer.send_and_wait(self.chat_topic, message)
                logger.info("Message sent successfully")
            except Exception as e:
                logger.error(f"Failed to send message to Kafka: {e}")
                logger.error(f"Message that failed: {message}")
        else:
            logger.warning("Kafka producer not initialized")

    async def broadcast_kafka_message(self, message: dict):
        """Kafka에서 수신한 메시지를 웹소켓 클라이언트에게 브로드캐스트합니다."""
        room_id = message.get("room_id")
        if room_id in self.active_connections:
            message_model = Message(**message)

            engine = await mongo.get_engine()
            if engine:
                await engine.save(message_model)

            for websocket in self.active_connections[room_id].values():
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Failed to send message to websocket: {e}")

    # async def consume_messages(self):
    #     """Kafka에서 메시지를 소비하여 웹소켓으로 브로드캐스트합니다."""
    #     if not self.consumer:
    #         logger.error("Kafka consumer is not initialized.")
    #         return
    #     try:
    #         while self._running:
    #             try:
    #                 async for message in self.consumer:
    #                     if not self._running:
    #                         break

    #                     if message and message.value:
    #                         try:
    #                             await self.broadcast_kafka_message(message.value)
    #                         except Exception as e:
    #                             logger.error(f"Error processing message: {e}")
    #                     else:
    #                         logger.warning("Received None or invalid message from Kafka")
    #             except asyncio.CancelledError:
    #                 logger.info("Consumer task cancelled")
    #                 break
    #             except Exception as e:
    #                 logger.error(f"Error in consumer loop: {e}")
    #                 await asyncio.sleep(1)  # Prevent tight loop on error

    #     except Exception as e:
    #         logger.error(f"Fatal error in consume_messages: {e}")
    #     finally:
    #         logger.info("Consumer task finished")

    async def consume_messages(self):
        """Kafka에서 메시지를 소비하여 웹소켓으로 브로드캐스트합니다."""
        logger.info("Starting to consume messages")
        if not self.consumer:
            logger.error("Kafka consumer is not initialized.")
            return

        try:
            while self._running:
                try:
                    async for msg in self.consumer:
                        if not self._running:
                            break

                        if msg and msg.value:
                            try:
                                # 바이트 메시지를 디코딩하고 파싱
                                message_data = json.loads(msg.value.decode("utf-8"))
                                logger.info(f"Received message: {message_data}")

                                await self.broadcast_kafka_message(message_data)
                            except json.JSONDecodeError as je:
                                logger.error(f"JSON Decode Error: {je}")
                                logger.error(f"Raw message value: {msg.value}")
                            except Exception as e:
                                logger.error(f"Error processing message: {e}")
                        else:
                            logger.warning("Received None or invalid message from Kafka")
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in consumer loop: {e}")
                    await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Fatal error in consume_messages: {e}")
        finally:
            logger.info("Consumer task finished")


manager = ConnectionManager()
