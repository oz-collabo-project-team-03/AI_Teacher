import logging
import pdb
import re
import string
from datetime import datetime
import random
from uuid import uuid4

from sqlalchemy.orm import joinedload
from ulid import ulid  # type: ignore
from fastapi import HTTPException
from sqlalchemy import select, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.common.models.tag import Tag
from src.app.common.utils.consts import SocialProvider, UserRole
from src.app.v1.user.entity.organization import Organization
from src.app.v1.user.entity.student import Student
from src.app.v1.user.entity.study_group import StudyGroup
from src.app.v1.user.entity.teacher import Teacher
from src.app.v1.user.entity.user import User

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class OAuthRepository:
    @staticmethod
    async def get_user_by_external_id(
        session: AsyncSession, external_id: str, social_provider: SocialProvider
    ) -> User | None:
        query = select(User).where(
            and_(
                User.external_id == external_id,
                User.social_provider == social_provider,
            )
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def get_user_by_id(self, session: AsyncSession, user_id: int) -> User | None:
        query = select(User).where(User.id == user_id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        return user

    async def get_user_by_email(self, session: AsyncSession, email: str):
        query = select(User).where(User.email == email)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        return user

    @staticmethod
    def generate_ulid(provider: str, user_id: str) -> str:
        unique_string = f"{provider}:{user_id}"
        ulid_value = ulid()
        return str(ulid_value)

    @staticmethod
    def format_phone_number(phone: str | None, provider: str = "default") -> str:
        if not phone or phone.strip() == "":
            ulid_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            provider_code = {"google": "99", "naver": "88", "kakao":"77"}.get(provider, "00")
            return f"010{provider_code}{ulid_suffix}"

        phone = phone.replace("-", "")
        if bool(re.match(r"^010\d{4}\d{4}$", phone)):
            return phone
        if phone.startswith("+82 "):
            return "0" + phone[4:]

        elif phone.startswith("+82"):
            return "0" + phone[3:]
        return phone

    async def get_user_with_info(self, user_id: int, session: AsyncSession):
        query = (
            select(User)
            .options(
                joinedload(User.student),
                joinedload(User.teacher).joinedload(Teacher.organization),
                joinedload(User.tag),
            )
            .where(User.id == user_id)
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()
        # user = result.scalars().first()
        # if not user:
        #     logger.warning(f"User with ID {user_id} not found.")
        # return user

    async def is_student_connected_to_teacher(self, student_id: int, session: AsyncSession) -> bool:
        query = (
            select(StudyGroup)
            .where(StudyGroup.student_id == student_id)
        )
        result = await session.execute(query)
        # StudyGroup에 해당 student_id가 존재하면 True, 없으면 False 반환
        return result.scalar_one_or_none() is not None


    async def update_student(self, user_id: int, student_data: dict, session: AsyncSession) -> User:
        try:
            user = await self.get_user_with_info(user_id, session)
            if not user:
                raise HTTPException(status_code=404, detail="유저를 찾을 수 없습니다.")

            if "nickname" in student_data:
                if user.tag:
                    user.tag.nickname = student_data["nickname"]
                else:
                    session.add(Tag(user_id=user.id, nickname=student_data["nickname"]))

            if user.student:
                student = user.student
            else:
                student = Student(user_id=user.id)
                session.add(student)

            for key, value in student_data.items():
                if hasattr(student, key):
                    setattr(student, key, value)

            user.first_login = False
            await session.commit()
            return user

        except IntegrityError as e:
            await session.rollback()
            raise HTTPException(status_code=400, detail="닉네임이 중복되었습니다.")
        except Exception as e:
            await session.rollback()
            raise HTTPException(status_code=500, detail="데이터베이스 오류가 발생했습니다.")

    async def update_teacher(self, user_id: int, teacher_data: dict, session: AsyncSession) -> User:
        try:
            user = await self.get_user_with_info(user_id, session)
            if not user:
                raise HTTPException(status_code=404, detail="유저를 찾을 수 없습니다.")

            if "nickname" in teacher_data:
                if user.tag:
                    user.tag.nickname = teacher_data["nickname"]
                else:
                    session.add(Tag(user_id=user.id, nickname=teacher_data["nickname"]))

            if user.teacher and user.teacher.organization:
                organization = user.teacher.organization
            else:
                if not user.teacher:
                    teacher = Teacher(user_id=user.id)
                    session.add(teacher)
                    user.teacher = teacher

                organization = Organization(teacher=user.teacher)
                session.add(organization)

            organization.name = teacher_data.get("organization_name")
            organization.type = teacher_data.get("organization_type")
            organization.position = teacher_data.get("position")

            user.first_login = False
            await session.commit()
            return user
        except IntegrityError as e:
            await session.rollback()
            raise HTTPException(status_code=400, detail="닉네임이 중복되었습니다.")
        except Exception as e:
            await session.rollback()
            raise HTTPException(status_code=500, detail="데이터베이스 오류가 발생했습니다.")
