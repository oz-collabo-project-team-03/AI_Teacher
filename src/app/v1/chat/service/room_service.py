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
    StudentInfo,
    TeacherInfo,
    TeacherStudentsResponse,
)

AI_PROFILE = "https://kr.object.ncloudstorage.com/backendsam/AI_Profile/AI.jpg"


class RoomService:

    def __init__(self, room_repository: RoomRepository):
        self.room_repository = room_repository

    async def create_room(self, request: RoomCreateRequest, user_id: int):
        student_id = await self.room_repository.user_exists(user_id)
        if not student_id:
            raise HTTPException(status_code=404, detail="학생 id를 찾을 수 없습니다.")
        teacher_id = await self.room_repository.get_teacher_id_with_student(user_id)
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
        teacher_id = await self.room_repository.get_teacher_id_with_student(user_id)
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


    async def get_students(self, user_id: int):
        # 1. Check if the user is a teacher
        teacher_id = await self.room_repository.user_exists(user_id)
        if not teacher_id:
            raise HTTPException(status_code=404, detail="선생 id를 찾을 수 없습니다.")

        # 2. Get teacher and students information
        results = await self.room_repository.get_teacher_and_students(teacher_id)

        # 3. Construct TeacherInfo from the results
        teacher_data = results["teacher"]
        teacher_info = TeacherInfo(
            teacher_id=teacher_data.teacher_id,
            teacher_image_url=teacher_data.teacher_image_url or "default_teacher_image.jpg",
            teacher_nickname=teacher_data.teacher_nickname,
        )

        # 4. Construct StudentInfo list from the results
        students_list = []
        for row in results["students"]:
            student_info = StudentInfo(
                room_id=row.room_id,
                student_id=row.student_id,  # 여기서 student_id는 User 테이블의 user_id
                student_nickname=row.student_nickname,
                student_image_url=row.student_image_url or "default_student_image.jpg",
                help_checked=row.help_checked if row.help_checked is not None else False,
            )
            students_list.append(student_info)

        # 5. Return the response model
        return TeacherStudentsResponse(teacher=teacher_info, students=students_list)

    # async def get_students(self, user_id: int):
    #     teacher_id = await self.room_repository.user_exists(user_id)
    #     if not teacher_id:
    #         raise HTTPException(status_code=404, detail="선생 id를 찾을 수 없습니다.")
    #     try:
    #         # 학생 및 방 정보 가져오기
    #         students_result = await self.room_repository.get_students_by_teacher(teacher_id)

    #         # 교사 정보 가져오기
    #         teacher_result = await self.room_repository.fetch_teacher_info(teacher_id)

    #         # 결과 정리
    #         rooms_info = []
    #         for row in students_result:
    #             room_info = RoomInfo(
    #                 room_id=row.room_id,
    #                 student_id=row.student_id,
    #                 student_nickname=row.student_nickname,
    #                 student_image_url=row.student_image_url or "default_student_image.jpg",
    #                 help_checked=row.help_checked,
    #             )
    #             rooms_info.append(room_info)

    #         teacher_info = TeacherInfo(
    #             teacher_id=teacher_id,
    #             teacher_image_url=(teacher_result.teacher_image_url if teacher_result else None) or "default_teacher_image.jpg",
    #             teacher_nickname=teacher_result.teacher_nickname if teacher_result else "선생님",
    #         )

    #         return TeacherStudentResponse(teacher=teacher_info, rooms=rooms_info)

    #     except Exception as e:
    #         raise HTTPException(status_code=500, detail=str(e))

    # 헬프 목록 조회
    async def room_help_list(self, mongo: AIOEngine, user_id: int) -> list[RoomHelpResponse] | None:
        teacher_id = await self.room_repository.user_exists(user_id)
        if not teacher_id:
            raise HTTPException(status_code=404, detail="선생 id를 찾을 수 없습니다.")

        return await self.room_repository.get_room_help_list(mongo, teacher_id)
