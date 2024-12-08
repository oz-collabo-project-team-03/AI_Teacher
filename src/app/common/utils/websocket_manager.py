import asyncio
import json
import logging
import os
from openai import AsyncOpenAI
from datetime import datetime
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from dotenv import load_dotenv
from fastapi import WebSocket, HTTPException
from sqlalchemy.future import select
from typing import Any
from src.app.common.utils.consts import UserRole
from src.app.v1.chat.entity.message import Message
from src.app.v1.chat.entity.room import Room
from src.config.database.mongo import MongoDB
from src.config.database.postgresql import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mongo = MongoDB()


load_dotenv()


class ConnectionManager:

    def __init__(self):
        self.active_connections: dict[int, dict[int, WebSocket]] = {}  # room_id: {user_id: websocket}
        self.mongo = mongo
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.client = AsyncOpenAI(api_key=self.openai_api_key)
        self.system_user_id = 0
        self.ai_user_id = 0
        self.ai_welcome_message = "AI 선생님과의 대화가 시작되었습니다. 궁금한 점을 물어보세요!"
        self.producer: AIOKafkaProducer | None = None
        self.consumer: AIOKafkaConsumer | None = None
        self.chat_topic = os.environ.get("CHAT_TOPIC")
        self._consumer_task = None
        self._running = False

        # 시스템 메시지 정의
        self.system_messages = {
            "ai_welcome": "AI 선생님과의 대화가 시작되었습니다. 궁금한 점을 물어보세요!",
            "teacher_welcome": "선생님과의 대화가 시작됩니다.",
            "ai_goodbye": "AI 선생님과의 대화가 종료되었습니다.",
            "teacher_goodbye": "선생님과의 대화가 종료되었습니다.",
            "ai_start_subject": "보고서 작성하는 게 너무 힘들지?^^ 도와줘?",
            "ai_start_menu": "시작할 메뉴를 입력해줘",
        }

    async def initialize(self, producer: AIOKafkaProducer, consumer: AIOKafkaConsumer):
        """Initialize the Kafka producer and consumer"""
        self.producer = producer
        self.consumer = consumer
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

    async def create_message(self, room: Room, user_id: int, user_type: str, content: str) -> dict:
        message = {
            "room_id": room.id,
            "title": room.title,
            "sender_id": user_id,
            "content": content,
            "message_type": "text",
            "user_type": user_type,
            "timestamp": datetime.now().isoformat(),
        }
        return message

    async def send_system_message(self, room: Room, message_type: str):
        message = {
            "room_id": room.id,
            "title": room.title,
            "sender_id": self.ai_user_id,
            "content": self.system_messages.get(message_type, ""),
            "message_type": "text",
            "user_type": "system",
            "timestamp": datetime.now().isoformat(),
        }
        await self.send_message(message)

    async def handle_help_check_update(self, room: Room, help_checked: bool):
        # 도움 요청 상태 변경에 따른 시스템 메시지 전송
        if help_checked:
            await self.send_system_message(room, "ai_goodbye")
            await self.send_system_message(room, "teacher_welcome")
        else:
            await self.send_system_message(room, "teacher_goodbye")
            await self.send_system_message(room, "ai_welcome")

    async def connect(self, websocket: WebSocket, room: Room, user_id: int, user_type: UserRole):
        await websocket.accept()

        if room.id not in self.active_connections:
            self.active_connections[room.id] = {}

        self.active_connections[room.id][user_id] = websocket

    async def handle_message(self, room: Room, user_id: int, user_type: str, content: str):
        print("=====================================================")
        print(f"handle check {room.help_checked}")
        print("=====================================================")
        try:
            if room.help_checked == False and user_type == "student" and user_id != None:
                await self.ai_chat(room, content)
                message = {
                    "room_id": room.id,
                    "title": room.title,
                    "sender_id": user_id,
                    "content": content,
                    "message_type": "text",
                    "user_type": user_type,
                    "timestamp": datetime.now().isoformat(),
                }
                await self.send_message(message)
            else:
                # 선생과 학생 대화
                message = {
                    "room_id": room.id,
                    "title": room.title,
                    "sender_id": user_id,
                    "content": content,
                    "message_type": "text",
                    "user_type": user_type,
                    "timestamp": datetime.now().isoformat(),
                }
                await self.send_message(message)
        except Exception as e:
            raise HTTPException(status_code=404, detail="Request의 정확한 전달이 필요합니다.")

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

    async def ai_chat(self, room: Room, content: str) -> Any:
        try:
            stream = await self.client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {"role": "user", "content": content},  # 사용자 메시지 추가
                ],
                stream=True,
            )

            buffer = ""
            collected_message = ""

            # 문장 끝을 나타내는 구두점들
            sentence_endings = [".", "!", "?", "\n"]
            BUFFER_SIZE = 50  # 또는 원하는 글자 수로 설정

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    chunk_content = chunk.choices[0].delta.content
                    buffer += chunk_content
                    collected_message += chunk_content

                    # 버퍼가 BUFFER_SIZE를 넘거나 문장이 완성되었을 때 전송
                    should_send = len(buffer) >= BUFFER_SIZE
                    ends_with_punctuation = any(buffer.rstrip().endswith(end) for end in sentence_endings)

                    if should_send or ends_with_punctuation:
                        if buffer.strip():
                            message = {
                                "room_id": room.id,
                                "title": room.title,
                                "sender_id": self.ai_user_id,
                                "content": buffer,
                                "message_type": "text",
                                "user_type": "ai",
                                "timestamp": datetime.now().isoformat(),
                            }
                            await self.send_message(message)
                        buffer = ""  # 버퍼 초기화

            # 남은 버퍼가 있다면 마지막으로 전송
            if buffer.strip():
                message = {
                    "room_id": room.id,
                    "title": room.title,
                    "sender_id": self.ai_user_id,
                    "content": buffer,
                    "message_type": "text",
                    "user_type": "ai",
                    "timestamp": datetime.now().isoformat(),
                }
                await self.send_message(message)

        except Exception as e:
            logger.error(f"OpenAI API Error: {e}")
            error_message = {
                "room_id": room.id,
                "title": room.title,
                "sender_id": self.ai_user_id,
                "content": "죄송합니다. 현재 AI 응답을 생성할 수 없습니다.",
                "message_type": "text",
                "user_type": "ai",
                "timestamp": datetime.now().isoformat(),
            }
            await self.send_message(error_message)

    async def send_message(self, message: dict):
        """Kafka에 메시지를 전송하고 웹소켓으로 브로드캐스트합니다."""
        if not message:  # None이거나 빈 딕셔너리인 경우 처리
            logger.error(f"{message}")
            logger.error("Received empty message")
            return
        if self.producer:
            try:
                # room_id를 파티션 키로 설정하여 순서 보장
                room_id = message.get("room_id")
                if room_id is None:
                    raise ValueError("Message must include 'room_id' to ensure partition consistency")

                # 메시지 전송 (room_id를 key로 설정)
                await self.producer.send_and_wait(
                    topic=self.chat_topic, key=str(room_id).encode("utf-8"), value=json.dumps(message).encode("utf-8")  # room_id를 파티션 키로 사용
                )
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
