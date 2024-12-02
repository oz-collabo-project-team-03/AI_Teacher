from fastapi import HTTPException
from odmantic import AIOEngine

from src.app.v1.chat.entity.room import Room
from src.app.v1.chat.repository.room_repository import RoomRepository
from src.app.v1.chat.schema.room_request import RoomCreateRequest
from src.app.v1.chat.schema.room_response import RoomCreateResponse


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

    async def ask_help(self, room_id: int, user_id: int) -> Room:
        is_student = await self.room_repository.check_user_student(user_id)
        if not is_student:
            raise HTTPException(status_code=404, detail=f"해당 User ID : {user_id}는 Student가 아닙니다.")
        try:
            updated_room = await self.room_repository.update_help_checked(room_id)
            return updated_room
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    async def get_room_messages(self, mongo: AIOEngine, room_id: int, user_id: str):
        pass
