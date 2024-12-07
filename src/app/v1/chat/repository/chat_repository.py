import logging

from sqlalchemy.exc import NoResultFound, SQLAlchemyError
from sqlalchemy.future import select

from src.app.v1.user.entity.user import User
from src.config.database.postgresql import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChatRepository:

    @classmethod
    async def get_user_role(cls, user_id):
        async with SessionLocal() as session:
            try:
                query = select(User.role).where(User.id == user_id)
                result = await session.execute(query)
                user_role = result.scalar_one_or_none()

                if user_role is None:
                    logger.warning(f"User ID: {user_id}가 존재하지 않습니다.")
                    return None

                return user_role

            except NoResultFound:
                logger.warning(f"User ID: {user_id}가 존재하지 않습니다.")
                return None
            except SQLAlchemyError as e:
                logger.error(f"Database error occurred: {e}")
                return None
            except Exception as e:
                logger.error(f"An unexpected error occurred: {e}")
                return None
