from datetime import datetime

from ulid import ulid  # type: ignore
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.common.models.tag import Tag
from src.app.common.utils.consts import SocialProvider, UserRole
from src.app.v1.user.entity.organization import Organization
from src.app.v1.user.entity.student import Student
from src.app.v1.user.entity.teacher import Teacher
from src.app.v1.user.entity.user import User


class OAuthRepository:
    @staticmethod
    async def get_user_by_external_id(
        session: AsyncSession, external_id: str, social_provider: SocialProvider
    ) -> User | None:
        result = await session.execute(
            select(User).where(
                User.external_id == external_id,
                User.social_provider == social_provider,
            )
        )
        return result.scalar()

    @staticmethod
    async def create_user(
            session: AsyncSession,
            external_id: str,
            email: str,
            phone: str,
            role: UserRole,
            social_provider: SocialProvider,
    ) -> User:
        first_login = True if role == UserRole.STUDENT else False

        user = User(
            external_id=external_id,
            email=email,
            phone=phone,
            role=role,
            social_provider=social_provider,
            first_login=first_login,
        )
        session.add(user)
        await session.flush()
        return user

    @staticmethod
    async def create_student(
            session: AsyncSession,
            user_id: int,
            nickname: str,
            school: str,
            career_aspiration: str,
            grade: int,
            description: str,
    ):
        student = Student(
            user_id=user_id,
            school=None,
            grade=0,
            career_aspiration=None,
            interest=None,
            description=None,
        )
        session.add(student)

        tag = Tag(user_id=user_id, nickname=nickname)
        session.add(tag)

    @staticmethod
    async def create_teacher(
            session: AsyncSession,
            user_id: int,
            nickname: None,
            organization_name: None,
            organization_type: None,
            position: None,
    ):
        teacher = Teacher(user_id=user_id)
        session.add(teacher)
        await session.flush()

        tag = Tag(user_id=user_id, nickname=nickname)
        session.add(tag)

        organization = Organization(
            teacher_id=teacher.id,
            name=organization_name,
            type=organization_type,
            position=position,
        )
        session.add(organization)

    @staticmethod
    async def update_user(
            session: AsyncSession, user: User, email: str, phone: str
    ) -> User:
        user.email = email
        user.phone = phone
        user.updated_at = datetime.now()
        user.first_login = False
        return user
