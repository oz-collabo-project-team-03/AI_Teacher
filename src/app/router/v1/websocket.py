import json
import logging
from fastapi import (
    APIRouter,
    HTTPException,
    WebSocket,
    WebSocketException,
    status,
)
from src.app.common.utils.websocket_manager import manager
from src.app.v1.chat.repository.chat_repository import ChatRepository
from src.app.v1.chat.repository.room_repository import RoomRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(tags=["Websocket"])


# Websocket
@router.websocket("/ws/{room_id}/{user_id}")
async def websocket(
    websocket: WebSocket,
    room_id: int,
    user_id: int,
    # current_user: dict = Depends(get_current_user_ws),
):
    try:
        user_id = user_id
        # if not current_user:
        #     await websocket.send_json({"error": "Authentication failed", "code": status.WS_1008_POLICY_VIOLATION})
        #     raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)

        if user_id is None:
            await websocket.send_json({"error": "User ID를 찾을 수 없습니다.", "code": status.WS_1008_POLICY_VIOLATION})
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="User ID를 찾을 수 없습니다.")

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

        await manager.connect(websocket, room, user_id)

        while True:
            data = await websocket.receive_text()
            try:
                message_data = json.loads(data)

                # 메시지 타입과 내용 추출
                message_type = message_data.get("message_type", "text")  # 기본값은 'text'
                content = message_data.get("content", "")
                filename = message_data.get("filename")  # 이미지인 경우 파일명

                print(f"{message_type}, {content}, {filename}")

            except json.JSONDecodeError:
                # JSON이 아닌 경우 텍스트 메시지로 처리
                message_type = "text"
                content = data
                filename = None

            # DB에서 최신 help_checked 상태 가져오기
            new_help_checked = await RoomRepository.get_help_checked_from_db(room_id)

            # 상태가 변경된 경우만 업데이트
            if room.help_checked != new_help_checked:
                room.help_checked = new_help_checked
                logger.info(f"Room {room_id} help_checked 상태가 업데이트됨: {room.help_checked}")

            if not await manager.can_send_message(room_id, user_type):
                logger.warning("당신은 선생이라 메시지를 보낼 수 없습니다.")
                continue

            await manager.handle_message(
                room=room, user_id=user_id, filename=filename, content=content, message_type=message_type, user_type=user_type
            )

    except HTTPException as he:
        await websocket.close(code=4004)
        logger.error(f"WebSocket connection error: {he.detail}")
    except WebSocketException as wse:
        await websocket.close(code=wse.code, reason=wse.reason)
        logger.error(f"WebSocket error: {wse.reason}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await manager.disconnect(room_id, user_id)
