import logging

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from src.app.common.models.tag import Tag
from src.app.common.utils.consts import UserRole
from src.app.common.utils.verify_password import hash_password
from src.app.v1.user.entity.organization import Organization
from src.app.v1.user.entity.student import Student
from src.app.v1.user.entity.teacher import Teacher
from src.app.v1.user.entity.user import User

logger = logging.getLogger(__name__)


class UserRepository:
    ALLOWED_USER_FIELDS = {"email", "password", "phone"}
    ALLOWED_STUDENT_FIELDS = {"school", "grade"}

    async def _get_user(self, session: AsyncSession, **kwargs) -> User | None:
        try:
            query = select(User).options(selectinload(User.student), selectinload(User.teacher))
            for key, value in kwargs.items():
                if key == "id":
                    value = int(value)  # user_id를 정수로 변환
                query = query.filter(getattr(User, key) == value)
            result = await session.execute(query)
            return result.scalars().first()
        except ValueError as e:
            logger.error(f"Invalid type for key {key}: {value}. Error: {e}")
            raise HTTPException(status_code=400, detail="잘못된 데이터 형식입니다.")
        except SQLAlchemyError as e:
            logger.error(f"Failed to fetch user: {e}")
            raise HTTPException(status_code=500, detail="데이터베이스 조회 중 오류가 발생했습니다.")

    async def get_user_by_id(self, session: AsyncSession, user_id: int) -> User | None:
        return await self._get_user(session, user_id=user_id)

    async def get_user_by_email(self, session: AsyncSession, email: str) -> User | None:
        return await self._get_user(session, email=email)

    async def get_user_email_by_phone(self, session: AsyncSession, phone: str) -> str | None:
        user = await self._get_user(session, phone=phone)
        return user.email if user else None

    async def create_student(self, session: AsyncSession, user_data: dict, student_data: dict):
        async with session.begin():
            try:
                user = User(
                    email=user_data["email"],
                    phone=user_data["phone"],
                    password=user_data["password"],
                    role=UserRole.STUDENT,
                    is_privacy_accepted=user_data["is_privacy_accepted"],
                )
                session.add(user)
                await session.flush()

                if nickname := user_data.get("nickname"):
                    tag = Tag(user_id=user.id, nickname=nickname)
                    session.add(tag)

                student = Student(
                    user_id=user.id,
                    school=student_data["school"],
                    grade=student_data.get("grade"),
                    career_aspiration=student_data.get("career_aspiration"),
                    interest=student_data.get("interest"),
                )
                session.add(student)

                return user
            except IntegrityError as e:
                logger.error(f"Integrity error: {e}")
                raise HTTPException(status_code=400, detail="중복된 데이터가 감지되었습니다.")
            except SQLAlchemyError as e:
                logger.error(f"Error creating student: {e}")
                raise HTTPException(status_code=500, detail="데이터베이스 오류가 발생했습니다.")

    async def create_teacher(self, session: AsyncSession, user_data: dict, teacher_data: dict):
        async with session.begin():
            try:
                user = User(
                    email=user_data["email"],
                    phone=user_data["phone"],
                    password=user_data["password"],
                    role=UserRole.TEACHER,
                    is_privacy_accepted=user_data["is_privacy_accepted"],
                )
                session.add(user)
                await session.flush()

                if nickname := user_data.get("nickname"):
                    tag = Tag(user_id=user.id, nickname=nickname)
                    session.add(tag)

                teacher = Teacher(user_id=user.id)
                session.add(teacher)
                await session.flush()

                organization = Organization(
                    name=teacher_data["organization_name"],
                    type=teacher_data["organization_type"],
                    position=teacher_data["position"],
                    teacher_id=teacher.id,
                )
                session.add(organization)

                return user
            except IntegrityError as e:
                logger.error(f"Integrity error: {e}")
                raise HTTPException(status_code=400, detail="중복된 데이터가 감지되었습니다.")
            except SQLAlchemyError as e:
                logger.error(f"Error creating teacher: {e}")
                raise HTTPException(status_code=500, detail="데이터베이스 오류가 발생했습니다.")

    async def update_user_password_with_temp(self, session: AsyncSession, email: str, temp_password: str) -> None:
        async with session.begin():
            try:
                user = await self.get_user_by_email(session, email)
                if not user:
                    raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
                user.password = hash_password(temp_password)
            except SQLAlchemyError as e:
                logger.error(f"Error updating password: {e}")
                raise HTTPException(status_code=500, detail="비밀번호 업데이트 중 오류가 발생했습니다.")

    async def update_user(self, session: AsyncSession, external_id: str, update_data: dict):
        async with session.begin():
            try:
                user = await self._get_user(session, id=external_id)
                if not user:
                    raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

                for field in self.ALLOWED_USER_FIELDS:
                    if field in update_data:
                        setattr(user, field, update_data[field])

                if user.role == UserRole.STUDENT:
                    student = user.student
                    if not student:
                        raise HTTPException(status_code=404, detail="학생 데이터를 찾을 수 없습니다.")
                    for field in self.ALLOWED_STUDENT_FIELDS:
                        if field in update_data:
                            setattr(student, field, update_data[field])

                return user
            except SQLAlchemyError as e:
                logger.error(f"Error updating user by external_id: {e}")
                raise HTTPException(status_code=500, detail="사용자 정보 업데이트 중 오류가 발생했습니다.")
