import logging

from datetime import datetime

from fastapi import HTTPException
from odmantic import AIOEngine, query
from sqlalchemy import and_, func
from sqlalchemy.exc import NoResultFound, SQLAlchemyError
from sqlalchemy.future import select
from sqlalchemy.orm import aliased

from src.config.database.mongo import MongoDB
from src.app.common.models.tag import Tag
from src.app.common.utils.consts import UserRole
from src.app.v1.chat.entity.message import Message
from src.app.v1.chat.entity.participant import Participant
from src.app.v1.chat.entity.room import Room
from src.app.v1.chat.schema.room_response import RoomHelpResponse, RoomListResponse
from src.app.v1.user.entity.student import Student
from src.app.v1.user.entity.study_group import StudyGroup
from src.app.v1.user.entity.teacher import Teacher
from src.app.v1.user.entity.user import User
from src.config.database.postgresql import SessionLocal
from src.app.common.utils.websocket_manager import manager

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mongo = MongoDB()


class RoomRepository:

    @classmethod
    async def room_exists(cls, room_id: int) -> int:
        async with SessionLocal() as session:
            try:
                query = select(Room).where(Room.id == room_id)
                result = await session.execute(query)
                room = result.scalar_one_or_none()

                return room is not None
            except NoResultFound:
                logger.warning(f"Room ID: {room_id}가 존재하지 않습니다.")
                return False
            except SQLAlchemyError as e:
                logger.error(f"Database error occurred: {e}")
                return False
            except Exception as e:
                logger.error(f"An unexpected error occurred: {e}")
                return False

    @classmethod
    async def get_room(cls, room_id: int) -> Room | None:
        async with SessionLocal() as session:
            try:
                query = select(Room).where(Room.id == room_id)
                result = await session.execute(query)
                room = result.scalar_one_or_none()

                return room

            except NoResultFound:
                logger.warning(f"Room: {room_id}가 존재하지 않습니다.")
                return None
            except SQLAlchemyError as e:
                logger.error(f"Database error occurred: {e}")
                return None
            except Exception as e:
                logger.error(f"An unexpected error occurred: {e}")
                return None

    @staticmethod
    async def user_exists(user_id: int) -> int:
        async with SessionLocal() as session:
            try:
                query = select(User).where(User.id == int(user_id))
                result = await session.execute(query)
                user = result.scalar_one_or_none()

                if user is None:
                    raise HTTPException(status_code=404, detail="해당 user ID : {user_id}는 존재하지 않습니다.")
                return user.id

            except SQLAlchemyError as e:
                logger.error(f"Database error occurred while fetching teacher ID: {e}")
                raise HTTPException(status_code=500, detail="DB 오류 발생")
            except Exception as e:
                logger.error(f"An unexpected error occurred: {e}")
                raise HTTPException(status_code=500, detail="{e}")

    @staticmethod
    async def check_user_student(user_id: int) -> bool:
        async with SessionLocal() as session:
            try:
                result = await session.execute(select(User.role).where(User.id == user_id))
                role = result.scalar_one_or_none()

                if role is None:
                    return False

                return role == UserRole.STUDENT
            except Exception as e:
                logger.error(f"Error checking user role: {e}")
                return False

    @staticmethod
    async def get_teacher_id_with_student(user_id: int) -> int | None:
        async with SessionLocal() as session:
            try:
                # user_id로 student를 찾고, 그 student의 student_group을 통해 teacher_id 조회
                query = (
                    select(StudyGroup.teacher_id)
                    .join(Student, Student.id == StudyGroup.student_id)
                    .join(User, User.id == Student.user_id)
                    .where(User.id == user_id)
                )
                result = await session.execute(query)
                teacher_id = result.scalar_one_or_none()  # 결과가 없으면 None 반환

                return teacher_id
            except SQLAlchemyError as e:
                logger.error(f"Database error occurred while fetching teacher ID: {e}")
                return None
            except Exception as e:
                logger.error(f"An unexpected error occurred: {e}")
                return None

    @staticmethod
    async def create_room_and_participant(request, student_id: int, teacher_id: int):
        async with SessionLocal() as session:
            # 새로운 방 생성
            new_room = Room(title=request.title, help_checked=False)

            # 세션에 방 추가
            session.add(new_room)
            await session.flush()

            # 참가자 추가
            participant = Participant(student_id=student_id, teacher_id=teacher_id, room_id=new_room.id)
            session.add(participant)

            await session.commit()

            # 처음 AI 메시지 출력 ( 출력되는 순서로 배치 )
            ai_start_message = {
                "room_id": new_room.id,
                "title": new_room.title,
                "sender_id": manager.ai_user_id,
                "content": manager.system_messages["ai_start_subject"],
                "filename": "None",
                "message_type": "text",
                "user_type": "ai",
                "timestamp": datetime.now().isoformat(),
            }
            ai_menu_message = {
                "room_id": new_room.id,
                "title": new_room.title,
                "sender_id": manager.ai_user_id,
                "content": manager.system_messages["ai_start_menu"],
                "filename": "None",
                "message_type": "text",
                "user_type": "ai",
                "timestamp": datetime.now().isoformat(),
            }
            welcome_message = {
                "room_id": new_room.id,
                "title": new_room.title,
                "sender_id": manager.system_user_id,
                "content": manager.system_messages["ai_welcome"],
                "filename": "None",
                "message_type": "text",
                "user_type": "system",
                "timestamp": datetime.now().isoformat(),
            }

            messages = [ai_menu_message, ai_start_message, welcome_message]
            for i in messages:
                message_model = Message(**i)

                engine = await mongo.get_engine()
                if engine:
                    await engine.save(message_model)

            return new_room

    @staticmethod
    async def delete_room_and_participant(room_id: int):
        async with SessionLocal() as session:
            try:
                # 방 찾기
                room = await session.get(Room, room_id)

                if not room:
                    raise HTTPException(status_code=404, detail=f"해당 Room ID: {room_id}는 존재하지 않습니다.")

                # 해당 방의 모든 참가자 찾기
                participants = await session.execute(select(Participant).where(Participant.room_id == room_id))
                participants = participants.scalars().all()

                # 모든 참가자 삭제
                for participant in participants:
                    await session.delete(participant)

                # 방 삭제
                await session.delete(room)

                await session.commit()

            except SQLAlchemyError as e:
                await session.rollback()
                raise HTTPException(status_code=500, detail=f"데이터베이스 오류: {str(e)}")

    @staticmethod
    async def update_help_checked(room_id: int) -> Room:
        async with SessionLocal() as session:
            try:
                query = select(Room).where(Room.id == room_id)
                result = await session.execute(query)
                room = result.scalar_one_or_none()

                if room is None:
                    raise HTTPException(status_code=404, detail="해당 Room ID : {room_id}는 존재하지 않습니다.")

                room.help_checked = not room.help_checked
                room.updated_at = func.now()

                await session.commit()

                # 상태 변경에 따른 시스템 메시지 전송
                await manager.handle_help_check_update(room, room.help_checked)

                logger.info(f"Room ID {room_id} help_checked 상태가 {room.help_checked}로 변경되었습니다.")

                return room

            except SQLAlchemyError as e:
                logger.error(f"Database error occurred while fetching teacher ID: {e}")
                raise HTTPException(status_code=500, detail="DB 오류 발생")
            except Exception as e:
                logger.error(f"An unexpected error occurred: {e}")
                raise HTTPException(status_code=500, detail="{e}")

    @staticmethod
    async def get_help_checked_from_db(room_id: int) -> bool:
        """PostgreSQL에서 Room의 help_checked 상태를 조회합니다."""
        async with SessionLocal() as session:
            try:
                query = select(Room).where(Room.id == room_id)
                result = await session.execute(query)
                room = result.scalar_one_or_none()

                if room is None:
                    logger.warning(f"Room {room_id}을(를) 찾을 수 없습니다.")
                    raise HTTPException(status_code=404, detail="해당 Room ID : {room_id}는 존재하지 않습니다.")

                return room.help_checked

            except Exception as e:
                logging.error(f"DB에서 help_checked 상태 조회 중 오류 발생: {e}")
                return False

    @staticmethod
    async def get_profile_images(room_id: int) -> tuple[str, str] | None:
        async with SessionLocal() as session:
            try:
                # User 테이블에 별칭 생성
                Student = aliased(User)
                Teacher = aliased(User)
                # room_id로 participant 조회하고 각각의 user 정보를 join
                query = (
                    select(Student.profile_image.label("student_profile"), Teacher.profile_image.label("teacher_profile"))
                    .join(Participant, Student.id == Participant.student_id)
                    .join(Teacher, Teacher.id == Participant.teacher_id, isouter=True)
                    .where(Participant.room_id == room_id)
                )

                result = await session.execute(query)
                profile_images = result.first()

                if not profile_images:
                    return None

                return profile_images.student_profile, profile_images.teacher_profile

            except SQLAlchemyError as e:
                logger.error(f"Database error occurred while fetching teacher ID: {e}")
                raise HTTPException(status_code=500, detail="DB 오류 발생")
            except Exception as e:
                logger.error(f"An unexpected error occurred: {e}")
                raise HTTPException(status_code=500, detail="{e}")

    @staticmethod
    async def get_nicknames_by_room_id(room_id: int) -> dict[str, str | None]:
        async with SessionLocal() as session:
            """
            room_id를 기준으로 Participant에서 student_id와 teacher_id를 가져와,
            해당 user에 연결된 Tag 엔티티에서 nickname을 조회합니다.

            Returns:
                dict[str, str | None]: 학생 및 교사의 닉네임.
                    {
                        "student_nickname": "학생 닉네임" or None,
                        "teacher_nickname": "교사 닉네임" or None
                    }
            """
            try:
                # room_id로 Participant에서 student_id와 teacher_id 가져오기
                participant = await session.execute(select(Participant.student_id, Participant.teacher_id).where(Participant.room_id == room_id))
                participant = participant.one_or_none()

                if not participant:
                    return {"student_nickname": None, "teacher_nickname": None}

                student_id, teacher_id = participant

                # student_id로 Tag의 nickname 조회
                student_tag = await session.execute(select(Tag.nickname).join(User).where(User.id == student_id))
                student_nickname = student_tag.scalar_one_or_none()

                # teacher_id로 Tag의 nickname 조회
                teacher_tag = await session.execute(select(Tag.nickname).join(User).where(User.id == teacher_id))
                teacher_nickname = teacher_tag.scalar_one_or_none()

                return {
                    "student_nickname": student_nickname,
                    "teacher_nickname": teacher_nickname,
                }
            except SQLAlchemyError as e:
                logger.error(f"Database error occurred: {e}")
                raise HTTPException(status_code=500, detail="DB 오류 발생")
            except Exception as e:
                logger.error(f"An unexpected error occurred: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def find_messages_by_room(room_id: int, mongo: AIOEngine, page: int = 1, page_size: int = 50) -> list[Message]:
        skip = (page - 1) * page_size
        messages = await mongo.find(Message, Message.room_id == room_id, sort=query.desc(Message.timestamp), skip=skip, limit=page_size)
        return list(messages)

    @staticmethod
    async def count_messages(room_id: int, mongo: AIOEngine) -> int:
        return await mongo.count(Message, Message.room_id == room_id)

    @staticmethod
    async def get_room_list(mongo: AIOEngine, user_id: int) -> list[RoomListResponse] | None:
        async with SessionLocal() as session:
            try:
                # 사용자가 참여한 방 목록 조회
                rooms = await session.execute(select(Room).join(Participant).where(Participant.student_id == user_id))
                rooms = rooms.scalars().all()

                result = []

                for room in rooms:
                    # 각 방의 최신 메시지 조회
                    recent_messages = await mongo.find(Message, Message.room_id == room.id, sort=query.desc(Message.timestamp), limit=1)
                    if recent_messages:
                        message = recent_messages[0]

                        room_response = RoomListResponse(
                            room_id=room.id,
                            title=room.title,
                            help_checked=room.help_checked,
                            recent_message=message.content,
                            recent_update=message.timestamp,
                            user_id=user_id,
                        )
                    else:
                        room_response = RoomListResponse(
                            room_id=room.id,
                            title=room.title,
                            help_checked=room.help_checked,
                            recent_message=None,
                            recent_update=None,
                            user_id=user_id,
                        )
                    result.append(room_response)

                return result

            except SQLAlchemyError as e:
                logger.error(f"Database error occurred while fetching teacher ID: {e}")
                raise HTTPException(status_code=500, detail="DB 오류 발생")
            except Exception as e:
                logger.error(f"An unexpected error occurred: {e}")
                raise HTTPException(status_code=500, detail="{e}")

    @staticmethod
    async def get_teacher_and_students(user_id: int):
        async with SessionLocal() as session:
            try:
                # 1. Get teacher info
                teacher_query = (
                    select(Teacher.id.label("teacher_id"), User.profile_image.label("teacher_image_url"), Tag.nickname.label("teacher_nickname"))
                    .join(User, Teacher.user_id == User.id)
                    .join(Tag, User.id == Tag.user_id)
                    .where(User.id == user_id)
                )

                # 2. 최신 Room ID를 가져오는 서브쿼리
                latest_rooms_subq = (
                    select(
                        Participant.student_id,
                        Room.id.label("room_id"),
                        Room.help_checked,
                        Room.updated_at,
                    )
                    .join(Room, Participant.room_id == Room.id)
                    .where(
                        and_(
                            Participant.teacher_id == user_id,  # 해당 선생님과 연결된 Room
                            Room.help_checked.is_(True),  # help_checked가 True인 Room
                        )
                    )
                    .distinct(Participant.student_id)  # 학생별로 한 개의 Room만 선택
                    .order_by(Participant.student_id, Room.updated_at.desc())  # 최신 Room 우선 정렬
                    .subquery()
                )

                # 3. 학생 정보와 Room 정보를 조회
                student_query = (
                    select(
                        Student.user_id.label("student_id"),
                        User.profile_image.label("student_image_url"),
                        Tag.nickname.label("student_nickname"),
                        func.coalesce(latest_rooms_subq.c.room_id, None).label("room_id"),
                        func.coalesce(latest_rooms_subq.c.help_checked, None).label("help_checked"),
                    )
                    .select_from(Teacher)
                    .join(StudyGroup, StudyGroup.teacher_id == Teacher.id)
                    .join(Student, Student.id == StudyGroup.student_id)
                    .join(User, Student.user_id == User.id)
                    .join(Tag, User.id == Tag.user_id)
                    .outerjoin(latest_rooms_subq, Student.user_id == latest_rooms_subq.c.student_id)
                    .where(Teacher.user_id == user_id)
                )
                # Execute queries
                teacher_result = await session.execute(teacher_query)
                student_result = await session.execute(student_query)

                return {"teacher": teacher_result.first(), "students": student_result.all()}
            except SQLAlchemyError as e:
                logger.error(f"Database error occurred while fetching teacher ID: {e}")
                raise HTTPException(status_code=500, detail=str(e))
            except Exception as e:
                logger.error(f"An unexpected error occurred: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def get_room_help_list(mongo: AIOEngine, user_id: int) -> list[RoomHelpResponse] | None:
        async with SessionLocal() as session:
            try:
                # teacher_user_id로 참여한 방 중 help_checked가 true인 방 목록 조회
                rooms = await session.execute(
                    select(Room).join(Participant).where(and_(Participant.teacher_id == user_id, Room.help_checked == True))
                )
                rooms = rooms.scalars().all()

                result = []

                for room in rooms:
                    # 각 방의 최신 메시지 조회
                    recent_messages = await mongo.find(Message, Message.room_id == room.id, sort=query.desc(Message.timestamp), limit=1)

                    # 해당 방에 참여한 student_id 조회
                    participants = await session.execute(select(Participant).where(Participant.room_id == room.id))
                    participant = participants.scalar_one_or_none()

                    # participant의 student_id로 Tag와 User를 통해 nickname 조회
                    nickname = None
                    if participant:
                        tags = await session.execute(select(Tag).join(User).where(User.id == participant.student_id))
                        tag = tags.scalar_one_or_none()
                        if tag:
                            nickname = tag.nickname

                    if recent_messages:
                        message = recent_messages[0]
                        room_response = RoomHelpResponse(
                            room_id=room.id,
                            student_id=participant.student_id if participant else None,
                            student_nickname=nickname,
                            help_checked=room.help_checked,
                            recent_message=message.content,
                            recent_update=message.timestamp,
                        )
                    else:
                        room_response = RoomHelpResponse(
                            room_id=room.id,
                            student_id=participant.student_id if participant else None,
                            student_nickname=nickname,
                            help_checked=room.help_checked,
                            recent_message=None,
                            recent_update=None,
                        )
                    result.append(room_response)

                return result if result else []

            except SQLAlchemyError as e:
                logger.error(f"Database error occurred while fetching teacher ID: {e}")
                raise HTTPException(status_code=500, detail=str(e))
            except Exception as e:
                logger.error(f"An unexpected error occurred: {e}")
                raise HTTPException(status_code=500, detail=str(e))
