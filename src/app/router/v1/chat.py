from fastapi import APIRouter, Depends
from src.app.common.utils.dependency import get_current_user
from src.app.v1.chat.schema.room_request import RoomCreateRequest
from src.app.v1.chat.schema.room_response import RoomCreateResponse
from src.app.v1.chat.service.room_service import RoomService
from src.app.common.factory import get_room_service

router = APIRouter(prefix="/chat", tags=["chats"])


# Create Room
@router.post("/create/room", response_model=RoomCreateResponse)
async def create_room(
    request: RoomCreateRequest,
    room_service: RoomService = Depends(get_room_service),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user.get("user_id")
    if user_id is None:
        raise ValueError("User ID는 None일 수 없습니다.")
    return await room_service.create_room(request, user_id=user_id)
