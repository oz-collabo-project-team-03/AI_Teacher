import logging
import os
from dotenv import load_dotenv
from datetime import datetime
from typing import TYPE_CHECKING
from src.app.v1.chat.entity.room import Room
from src.app.v1.chat.schema.websocket_response import MessageResponse

from src.app.common.utils.consts import UserRole

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

if TYPE_CHECKING:
    from src.app.common.utils.websocket_manager import ConnectionManager


class ChatService:

    async def create_message(self, room: Room, user_id: int, user_type: UserRole, content: str) -> dict:
        now = datetime.now()
        return {
            "room_id": room.id,
            "title": room.title,
            "sender_id": user_id,
            "content": content,
            "message_type": "text",
            "user_type": user_type.value,
            "timestamp": now.strftime("%Y-%m-%d %H시%M분"),
        }

    async def process_message(self, manager: "ConnectionManager", message: dict, room: Room, user_type: UserRole):
        if not room.help_checked and user_type == UserRole.STUDENT:
            # FIXME: AI 코드 미완성
            # ai_response = await manager.ai_chat(message["content"])
            now = datetime.now()

            ai_response = "아직 완성되지 않은 AI"
            ai_message = {
                "room_id": room.id,
                "title": room.title,
                "sender_id": os.getenv("AI_USER_ID"),
                "content": ai_response,
                "message_type": "text",
                "user_type": "ai",
                "timestamp": now.strftime("%Y-%m-%d %H시%M분"),
            }
            await manager.send_message(ai_message)
            logger.info(f"Sending message: {message}")
