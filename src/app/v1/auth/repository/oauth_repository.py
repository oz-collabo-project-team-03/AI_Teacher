import logging
import pdb
import re
from datetime import datetime
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
            ulid_suffix = str(uuid4().int)[:8]  # ULID의 일부를 사용해 유니크한 값 생성
            provider_code = {"google": "99", "facebook": "88"}.get(provider, "00")
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

    async def update_student(self, user_id: int, student_data: dict, session: AsyncSession) -> User:
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

    async def update_teacher(self, user_id: int, teacher_data: dict, session: AsyncSession) -> User:
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

    # async def update_student(self, user_id: int, student_data: dict, session: AsyncSession) -> User:
    #     user = await self.get_user_with_info(user_id, session)
    #     if not user:
    #         logger.warning(f"User with ID {user_id} not found.")
    #         raise HTTPException(status_code=404, detail="유저를 찾을 수 없습니다.")
    #
    #     if "nickname" in student_data:
    #         if user.tag:
    #             user.tag.nickname = student_data["nickname"]
    #         else:
    #             new_tag = Tag(user_id=user.id, nickname=student_data["nickname"])
    #             session.add(new_tag)
    #
    #     if "profile_image" in student_data:
    #         user.profile_image = student_data["profile_image"]
    #
    #     if user.student:
    #         student = user.student
    #         if "career_aspiration" in student_data:
    #             student.career_aspiration = student_data["career_aspiration"]
    #         if "interest" in student_data:
    #             student.interest = student_data["interest"]
    #         if "description" in student_data:
    #             student.description = student_data["description"]
    #         if "school" in student_data:
    #             student.school = student_data["school"]
    #         if "grade" in student_data:
    #             student.grade = student_data["grade"]
    #
    #     user.first_login = False
    #
    #     await session.flush()
    #     logger.info(f"User profile updated successfully for user_id={user_id}")
    #     return user
    #
    #
    # async def update_teacher(self, user_id: int, teacher_data: dict, session: AsyncSession) -> User:
    #     user = await self.get_user_with_info(user_id, session)
    #     if not user:
    #         print(f"User with ID {user_id} not found.")
    #         raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    #
    #     if "nickname" in teacher_data:
    #         if user.tag:
    #             user.tag.nickname = teacher_data["nickname"]
    #         else:
    #             new_tag = Tag(user_id=user.id, nickname=teacher_data["nickname"])
    #             session.add(new_tag)
    #
    #     if "profile_image" in teacher_data:
    #         user.profile_image = teacher_data["profile_image"]
    #
    #     if user.teacher and user.teacher.organization:
    #         organization = user.teacher.organization
    #         if "organization_name" in teacher_data:
    #             organization.name = teacher_data["organization_name"]
    #         if "organization_type" in teacher_data:
    #             organization.type = teacher_data["organization_type"]
    #         if "position" in teacher_data:
    #             organization.position = teacher_data["position"]
    #
    #     user.first_login = False
    #
    #     await session.flush()
    #     print(f"Teacher profile updated successfully for user_id={user_id}")
    #     return user
