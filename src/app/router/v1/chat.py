from fastapi import APIRouter, Depends, HTTPException, status
from odmantic import AIOEngine

from src.app.common.factory import get_room_service, mongo_db
from src.app.common.utils.dependency import get_current_user
from src.app.v1.chat.entity.message import Message
from src.app.v1.chat.schema.room_request import RoomCreateRequest
from src.app.v1.chat.schema.room_response import RoomCreateResponse, RoomListResponse, RoomHelpResponse, RoomHelpUpdateResponse
from src.app.v1.chat.service.room_service import RoomService

router = APIRouter(tags=["Chats"])


# Create Room
@router.post("/chat/room", response_model=RoomCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_room(
    request: RoomCreateRequest,
    room_service: RoomService = Depends(get_room_service),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user.get("user_id")
    if user_id is None:
        raise HTTPException(status_code=404, detail="User ID는 None일 수 없습니다.")
    return await room_service.create_room(request, user_id=int(user_id))


# Delete Room
@router.delete("/chat/room/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room(
    room_id: int,
    room_service: RoomService = Depends(get_room_service),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user.get("user_id")
    if user_id is None:
        raise HTTPException(status_code=404, detail="User ID는 None일 수 없습니다.")
    return await room_service.delete_room(room_id=room_id, user_id=int(user_id))


# Ask Help
@router.patch("/chat/help/{room_id}", response_model=RoomHelpUpdateResponse)
async def ask_help(
    room_id: int,
    room_service: RoomService = Depends(get_room_service),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user.get("user_id")
    if user_id is None:
        raise HTTPException(status_code=404, detail="User ID는 찾을 수 없습니다.")
    return await room_service.ask_help(room_id=room_id, user_id=int(user_id))


# Get Rooms about Student
@router.get("/chat/students", response_model=list[RoomListResponse])
async def get_rooms_student(
    mongo: AIOEngine = Depends(mongo_db),
    room_service: RoomService = Depends(get_room_service),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user.get("user_id")
    if user_id is None:
        raise HTTPException(status_code=404, detail="User ID는 None일 수 없습니다.")
    return await room_service.get_rooms_student(mongo, user_id=int(user_id))


# Get Room
@router.get("/chat/{room_id}/messages")
async def get_room_messages(
    room_id: int,
    mongo: AIOEngine = Depends(mongo_db),
    room_service: RoomService = Depends(get_room_service),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user.get("user_id")
    if user_id is None:
        raise HTTPException(status_code=404, detail="User ID는 None일 수 없습니다.")
    return await room_service.get_room_messages(mongo, room_id=room_id, user_id=user_id)


# 메시지 조회 엔드포인트
@router.get("/chat/{room_id}/messages")
async def read_message(
    room_id: int,
    mongo: AIOEngine = Depends(mongo_db),
    current_user: dict = Depends(get_current_user),
):
    message = await mongo.find(Message, Message.room_id == room_id)
    if message:
        return message
    return {"error": "Message not found"}


# 관리 학생 목록 조회
@router.get("/teacher/students", response_model="")
async def get_students():
    pass


# 헬프 목록 조회
@router.get("/teacher/helps", response_model=list[RoomHelpResponse])
async def get_help_list(
    mongo: AIOEngine = Depends(mongo_db),
    room_service: RoomService = Depends(get_room_service),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user.get("user_id")
    if user_id is None:
        raise HTTPException(status_code=404, detail="User ID는 None일 수 없습니다.")
    return await room_service.room_help_list(mongo, user_id=int(user_id))
