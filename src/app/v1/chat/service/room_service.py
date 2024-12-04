from fastapi import HTTPException
from odmantic import AIOEngine
from src.app.v1.chat.repository.room_repository import RoomRepository
from src.app.v1.chat.schema.room_request import RoomCreateRequest
from src.app.v1.chat.schema.room_response import (
    RoomCreateResponse,
    RoomListResponse,
    RoomHelpResponse,
    RoomHelpUpdateResponse,
    RoomMessagesListResponse,
)

AI_PROFILE = "https://kr.object.ncloudstorage.com/backendsam/AI_Profile/AI.jpg"


class RoomService:

    def __init__(self, room_repository: RoomRepository):
        self.room_repository = room_repository

    async def create_room(self, request: RoomCreateRequest, user_id: int):
        student_id = await self.room_repository.user_exists(user_id)
        if not student_id:
            raise HTTPException(status_code=404, detail="학생 id를 찾을 수 없습니다.")
        teacher_id = await self.room_repository.get_teacher_id(user_id)
        if not teacher_id:
            raise HTTPException(status_code=404, detail="등록된 선생 id를 찾을 수 없습니다.")

        # 방과 참가자 생성
        new_room = await self.room_repository.create_room_and_participant(request, student_id, teacher_id)
        return RoomCreateResponse(
            room_id=new_room.id,
            title=new_room.title,
            help_checked=new_room.help_checked,
            student_id=student_id,
            teacher_id=teacher_id,
        )

    async def delete_room(self, room_id: int, user_id: int):
        student_id = await self.room_repository.user_exists(user_id)
        if not student_id:
            raise HTTPException(status_code=404, detail="학생 id를 찾을 수 없습니다.")
        teacher_id = await self.room_repository.get_teacher_id(user_id)
        if not teacher_id:
            raise HTTPException(status_code=404, detail="등록된 선생 id를 찾을 수 없습니다.")

        return await self.room_repository.delete_room_and_participant(room_id)

    async def ask_help(self, room_id: int, user_id: int) -> RoomHelpUpdateResponse:
        is_student = await self.room_repository.check_user_student(user_id)
        if not is_student:
            raise HTTPException(status_code=404, detail=f"해당 User id : {user_id}는 Student가 아닙니다.")
        try:
            room = await self.room_repository.update_help_checked(room_id)
            return RoomHelpUpdateResponse(
                room_id=room.id,
                title=room.title,
                help_checked=room.help_checked,
                created_at=room.created_at,
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    async def get_rooms_student(self, mongo: AIOEngine, user_id: int) -> list[RoomListResponse] | None:
        student_id = await self.room_repository.user_exists(user_id)
        if not student_id:
            raise HTTPException(status_code=404, detail="학생 id를 찾을 수 없습니다.")

        return await self.room_repository.get_room_list(mongo, user_id)

    async def get_room_messages(self, mongo: AIOEngine, page: int, page_size: int, room_id: int) -> RoomMessagesListResponse | None:
        is_room = await self.room_repository.get_room(room_id=room_id)
        if not is_room:
            raise HTTPException(status_code=404, detail="채팅방 id를 찾을 수 없습니다.")

        profiles = await self.room_repository.get_profile_images(room_id)
        if not profiles:
            raise HTTPException(status_code=404, detail="Profile을 찾을 수 없습니다.")

        nicknames = await self.room_repository.get_nicknames_by_room_id(room_id)
        if not nicknames:
            raise HTTPException(status_code=404, detail="닉네임을 찾을 수 없습니다.")
        student_nickname = nicknames.get("student_nickname", "학생")
        teacher_nickname = nicknames.get("teacher_nickname", "교사")

        student_profile, teacher_profile = profiles

        messages = await self.room_repository.find_messages_by_room(room_id, mongo, page, page_size)
        total_messages = await self.room_repository.count_messages(room_id, mongo)
        total_pages = (total_messages + page_size - 1) // page_size

        return RoomMessagesListResponse.from_room_and_messages(
            room=is_room,
            messages=messages,
            ai_profile=AI_PROFILE,
            student_profile=student_profile or "default_student_image.jpg",
            teacher_profile=teacher_profile or "default_teacher_image.jpg",
            student_nickname=student_nickname or "학생",
            teacher_nickname=teacher_nickname or "선생님",
            page=page,
            total_pages=total_pages,
            total_messages=total_messages,
        )

    # 관리 학생 목록 조회
    async def get_students(self, mongo: AIOEngine, room_id: int, user_id: int):
        pass

    # 헬프 목록 조회
    async def room_help_list(self, mongo: AIOEngine, user_id: int) -> list[RoomHelpResponse] | None:
        teacher_id = await self.room_repository.user_exists(user_id)
        if not teacher_id:
            raise HTTPException(status_code=404, detail="선생 id를 찾을 수 없습니다.")

        return await self.room_repository.get_room_help_list(mongo, teacher_id)
