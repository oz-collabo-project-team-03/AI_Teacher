import logging

from sqlalchemy.exc import NoResultFound, SQLAlchemyError
from sqlalchemy import func
from sqlalchemy.future import select
from odmantic import AIOEngine, query
from fastapi import HTTPException
from datetime import datetime
from src.app.v1.chat.entity.message import Message
from src.app.v1.chat.entity.participant import Participant
from src.app.v1.chat.entity.room import Room
from src.app.v1.user.entity.student import Student
from src.app.v1.user.entity.study_group import StudyGroup
from src.app.v1.user.entity.user import User
from src.app.v1.chat.entity.room import Room
from src.config.database.postgresql import SessionLocal
from src.app.common.utils.consts import UserRole
from src.app.v1.chat.schema.room_response import RoomListResponse

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
                print(f"role이 뭐냐 : {role}")

                if role is None:
                    return False

                return role == UserRole.STUDENT
            except Exception as e:
                logger.error(f"Error checking user role: {e}")
                return False

    @staticmethod
    async def get_teacher_id(user_id: int) -> int | None:
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
                return room

            except SQLAlchemyError as e:
                logger.error(f"Database error occurred while fetching teacher ID: {e}")
                raise HTTPException(status_code=500, detail="DB 오류 발생")
            except Exception as e:
                logger.error(f"An unexpected error occurred: {e}")
                raise HTTPException(status_code=500, detail="{e}")

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
                        date_object = datetime.strptime(message.timestamp, "%m-%d-%H-%M")
                        formatted_date = date_object.strftime("%m-%d-%H-%M")
                        room_response = RoomListResponse(
                            room_id=room.id,
                            title=room.title,
                            help_checked=room.help_checked,
                            recent_message=message.content,
                            recent_update=formatted_date,
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
