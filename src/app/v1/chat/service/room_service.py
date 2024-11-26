from fastapi import HTTPException
from src.app.v1.chat.schema.room_request import RoomCreateRequest
from src.app.v1.chat.schema.room_response import RoomCreateResponse
from src.app.v1.chat.repository.room_repository import RoomRepository


class RoomService:

    def __init__(self, room_repository: RoomRepository):
        self.room_repository = room_repository

    async def create_room(self, request: RoomCreateRequest, user_id: str):
        student_id = await self.room_repository.user_exists(user_id)
        if not student_id:
            raise HTTPException(status_code=404, detail="학생 id를 찾을 수 없습니다.")
        teacher_id = await self.room_repository.get_teacher_id(user_id)
        if not teacher_id:
            raise HTTPException(status_code=404, detail="등록된 선생 id를 찾을 수 없습니다.")

        user_list = [student_id, teacher_id]

        # 방과 참가자 생성
        new_room = await self.room_repository.create_room_and_participant(request, user_list)

        # 응답 데이터 생성
        participants = []

        participants.append({"student_id": user_list[0]})
        participants.append({"teacher_id": user_list[1]})

        response = RoomCreateResponse(room_id=new_room.id, title=new_room.title, help_checked=new_room.help_checked, participants=participants)

        return response
