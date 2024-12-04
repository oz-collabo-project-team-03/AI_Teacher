import logging
from fastapi import APIRouter, WebSocket, HTTPException

from src.app.v1.chat.repository.room_repository import RoomRepository
from src.app.v1.chat.repository.chat_repository import ChatRepository
from src.app.v1.chat.service.chat import ChatService
from src.app.common.utils.websocket_manager import manager
from src.app.common.utils.consts import UserRole


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(tags=["Websocket"])

chat_service = ChatService()


# Websocket
@router.websocket("/ws/{room_id}/{user_id}")
async def websocket(
    websocket: WebSocket,
    room_id: int,
    user_id: int,
):
    try:
        # TODO: user_id를 따로 찾아서 검증
        # user_id = current_user.get("user_id")
        user_id = user_id
        if user_id is None:
            await websocket.send_text("User ID를 찾을 수 없습니다. 연결이 끊어집니다.")
            await websocket.close(code=4004)
            return

        room = await RoomRepository.get_room(room_id=room_id)
        if room is None:
            await websocket.send_text("Room ID를 찾을 수 없습니다. 연결이 끊어집니다.")
            await websocket.close(code=4004)
            return

        user_type = await ChatRepository.get_user_role(user_id=user_id)
        if user_type is None:
            await websocket.send_text("User Role를 찾을 수 없습니다. 연결이 끊어집니다.")
            await websocket.close(code=4004)
            return

        await manager.connect(websocket, room_id, user_id, user_type)

        while True:
            data = await websocket.receive_text()

            if not await manager.can_send_message(room_id, user_type):
                print("당신은 선생이라 메시지를 보낼 수 없습니다.")
                continue

            message = await chat_service.create_message(room, user_id, user_type, data)
            # help_checked가 True일 때 AI의 답변을 보내지 않도록 조건 추가
            if room.help_checked and (user_type == UserRole.STUDENT or user_type == UserRole.TEACHER):
                await manager.send_message(message)  # 선생과 학생 간의 대화 전송
                logger.info(f"Sending message: {message}")
                continue

            # AI의 답변 처리
            await chat_service.process_message(manager, message, room, user_type)

    except HTTPException as he:
        await websocket.close(code=4004)
        logger.error(f"WebSocket connection error: {he.detail}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await manager.disconnect(room_id, user_id)
