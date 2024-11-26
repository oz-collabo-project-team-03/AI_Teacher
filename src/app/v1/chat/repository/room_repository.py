from sqlalchemy.future import select
from src.app.v1.chat.entity import participant
from src.app.v1.user.entity.user import User
from src.app.v1.chat.entity.room import Room
from src.app.v1.chat.entity.participant import Participant
from src.config.database.postgresql import SessionLocal
from src.app.v1.user.entity.student import Student
from src.app.v1.user.entity.study_group import StudyGroup
from sqlalchemy.exc import NoResultFound, SQLAlchemyError
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RoomRepository:

    @staticmethod
    async def user_exists(user_id: str) -> bool:
        async with SessionLocal() as session:
            try:
                query = select(User).where(User.id == int(user_id))
                result = await session.execute(query)
                user = result.scalar_one_or_none()

                return user is not None
            except NoResultFound:
                logger.warning(f"User with ID {user_id} does not exist.")
                return False
            except SQLAlchemyError as e:
                logger.error(f"Database error occurred: {e}")
                return False
            except Exception as e:
                logger.error(f"An unexpected error occurred: {e}")
                return False

    @staticmethod
    async def get_teacher_id(user_id: str) -> int | None:
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
            except NoResultFound:
                logger.warning(f"No study group found for user ID {user_id}.")
                return None
            except SQLAlchemyError as e:
                logger.error(f"Database error occurred while fetching teacher ID: {e}")
                return None
            except Exception as e:
                logger.error(f"An unexpected error occurred: {e}")
                return None

    @staticmethod
    async def create_room_and_participant(request, user_list: list[int]):
        async with SessionLocal() as session:
            # 새로운 방 생성
            new_room = Room(title=request.title, help_checked=False)

            # 세션에 방 추가
            session.add(new_room)
            await session.flush()

            # 참가자 추가
            for user_id in user_list:
                participant = Participant(user_uid=user_id, room_id=new_room.id)
                session.add(participant)

            await session.commit()
            return new_room
