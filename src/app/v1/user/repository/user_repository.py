import logging

# from src.app.common.utils.image import NCPStorageService
from email_validator import EmailNotValidError, validate_email
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncResult, AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from ulid import ulid  # type: ignore

from src.app.common.models.tag import Tag
from src.app.common.utils.consts import UserRole
from src.app.common.utils.verify_password import (
    hash_password,
    validate_password_complexity,
)
from src.app.v1.post.entity.post import Post
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
        return await self._get_user(session, id=user_id)

    async def get_user_by_external_id(self, session: AsyncSession, external_id: str) -> User | None:
        return await self._get_user(session, id=external_id)

    async def get_user_by_email(self, session: AsyncSession, email: str) -> User | None:
        return await self._get_user(session, email=email)

    async def get_user_email_by_phone(self, session: AsyncSession, phone: str) -> str | None:
        user = await self._get_user(session, phone=phone)
        return user.email if user else None

    async def get_user_posts(self, session: AsyncSession, user_id: int) -> list[Post]:
        try:
            user = await session.get(User, user_id)
            if not user:
                raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
            return user.posts
        except Exception as e:
            logger.error(f"Error fetching posts for user_id={user_id}: {e}")
            raise HTTPException(status_code=500, detail="사용자 게시물 조회 중 오류가 발생했습니다.")

    async def create_student(self, session: AsyncSession, user_data: dict, student_data: dict):
        async with session.begin():
            try:
                user = User(
                    external_id=ulid(),
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
                error_detail = str(e.orig).lower()

                if "email" in error_detail:
                    detail = "중복된 이메일이 존재합니다."
                elif "phone" in error_detail:
                    detail = "중복된 전화번호가 존재합니다."
                elif "nickname" in error_detail:
                    detail = "중복된 닉네임이 존재합니다."
                else:
                    detail = "중복된 데이터가 감지되었습니다."

                raise HTTPException(status_code=400, detail=detail)
            except SQLAlchemyError as e:
                logger.error(f"Error creating student: {e}")
                raise HTTPException(status_code=500, detail="데이터베이스 오류가 발생했습니다.")

    async def create_teacher(self, session: AsyncSession, user_data: dict, teacher_data: dict):
        async with session.begin():
            try:
                user = User(
                    external_id=ulid(),
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
                error_detail = str(e.orig).lower()

                if "email" in error_detail:
                    detail = "중복된 이메일이 존재합니다."
                elif "phone" in error_detail:
                    detail = "중복된 전화번호가 존재합니다."
                elif "nickname" in error_detail:
                    detail = "중복된 닉네임이 존재합니다."
                else:
                    detail = "중복된 데이터가 감지되었습니다."

                raise HTTPException(status_code=400, detail=detail)

            except SQLAlchemyError as e:
                logger.error(f"Error creating teacher: {e}")
                raise HTTPException(status_code=500, detail="데이터베이스 오류가 발생했습니다.")

    async def reset_user_password(self, session: AsyncSession, email: str, temp_password: str):
        async with session.begin():
            try:
                user = await self.get_user_by_email(session, email)
                if not user:
                    raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

                user.password = hash_password(temp_password)
                logger.info(f"사용자 비밀번호 업데이트 완료. email: {email}")
            except Exception as e:
                logger.error(f"비밀번호 업데이트 중 오류 발생: {e}")
                raise

    # 교사 회원정보 조회 -> 이메일, 패스워드, 전화번호
    async def get_teacher_info(self, session: AsyncSession, user_id: int) -> dict:
        try:
            user = await self.get_user_by_id(session, user_id)
            if not user or user.role != UserRole.TEACHER:
                logger.error(f"교사 정보를 찾을 수 없습니다: user_id={user_id}")
                raise HTTPException(status_code=404, detail="교사 정보를 찾을 수 없습니다.")

            teacher_info = {
                "email": user.email,
                "password": user.password,
                "phone": user.phone,
            }
            logger.info(f"교사 정보 조회 성공: user_id={user_id}, teacher_info={teacher_info}")
            return teacher_info
        except SQLAlchemyError as e:
            logger.error(f"교사 정보 조회 중 오류 발생: user_id={user_id}, error={e}")
            raise HTTPException(status_code=500, detail="교사 정보 조회 중 데이터베이스 오류가 발생했습니다.")

    async def get_student_info(self, session: AsyncSession, user_id: int) -> dict:
        try:
            user = await self.get_user_by_id(session, user_id)
            if not user or user.role != UserRole.STUDENT:
                logger.error(f"학생 정보를 찾을 수 없습니다: user_id={user_id}")
                raise HTTPException(status_code=404, detail="학생 정보를 찾을 수 없습니다.")

            student = user.student
            if not student:
                logger.error(f"학생 데이터를 찾을 수 없습니다: user_id={user_id}")
                raise HTTPException(status_code=404, detail="학생 데이터를 찾을 수 없습니다.")

            student_info = {
                "email": user.email,
                "password": user.password,
                "phone": user.phone,
                "school": student.school,
                "grade": student.grade,
            }
            logger.info(f"학생 정보 조회 성공: user_id={user_id}, student_info={student_info}")
            return student_info
        except SQLAlchemyError as e:
            logger.error(f"학생 정보 조회 중 오류 발생: user_id={user_id}, error={e}")
            raise HTTPException(status_code=500, detail="학생 정보 조회 중 데이터베이스 오류가 발생했습니다.")

    async def update_teacher_info(self, session: AsyncSession, user_id: int, update_data: dict):
        async with session.begin():
            try:
                user = await self.get_user_by_id(session, user_id)
                if not user or user.role != UserRole.TEACHER:
                    logger.error(f"교사 정보를 찾을 수 없습니다: user_id={user_id}")
                    raise HTTPException(status_code=404, detail="교사 정보를 찾을 수 없습니다.")

                for field, value in update_data.items():
                    setattr(user, field, value)

                logger.info(f"교사 정보 업데이트 성공: user_id={user_id}, update_data={update_data}")
            except SQLAlchemyError as e:
                logger.error(f"교사 정보 업데이트 중 오류 발생: user_id={user_id}, error={e}")
                raise HTTPException(status_code=500, detail="교사 정보 업데이트 중 데이터베이스 오류가 발생했습니다.")

    async def update_student_info(self, session: AsyncSession, user_id: int, common_fields: dict, student_fields: dict):
        async with session.begin():
            try:
                user = await self.get_user_by_id(session, user_id)
                if not user or user.role != UserRole.STUDENT:
                    logger.error(f"학생 정보를 찾을 수 없습니다: user_id={user_id}")
                    raise HTTPException(status_code=404, detail="학생 정보를 찾을 수 없습니다.")

                for field, value in common_fields.items():
                    setattr(user, field, value)

                student = user.student
                if not student:
                    logger.error(f"학생 데이터를 찾을 수 없습니다: user_id={user_id}")
                    raise HTTPException(status_code=404, detail="학생 데이터를 찾을 수 없습니다.")

                for field, value in student_fields.items():
                    setattr(student, field, value)

                logger.info(f"학생 정보 업데이트 성공: user_id={user_id}, common_fields={common_fields}, student_fields={student_fields}")
            except SQLAlchemyError as e:
                logger.error(f"학생 정보 업데이트 중 오류 발생: user_id={user_id}, error={e}")
                raise HTTPException(status_code=500, detail="학생 정보 업데이트 중 데이터베이스 오류가 발생했습니다.")


#     storage_service = NCPStorageService()
#     # 프로필 조회
#     async def get_student_profile(self, session: AsyncSession, user_id: int) -> dict:
#         result = await session.execute(
#             select(Student).where(Student.user_id == user_id)
#         )
#         student = result.scalars().first()
#
#         if not student:
#             raise HTTPException(status_code=404, detail="학생 데이터를 찾을 수 없습니다.")
#
#         profile_data = {
#             "school": student.school,
#             "grade": student.grade,
#             "career_aspiration": student.career_aspiration,
#             "interest": student.interest,
#             "description": student.description,
#         }
#
#         return profile_data
#
#     async def get_teacher_profile(self, session: AsyncSession, user_id: int) -> dict:
#         result = await session.execute(
#             select(Teacher).where(Teacher.user_id == user_id)
#         )
#         teacher = result.scalars().first()
#
#         if not teacher or not teacher.organization:
#             raise HTTPException(status_code=404, detail="교사 데이터를 찾을 수 없습니다.")
#
#         profile_data = {
#             "organization_name": teacher.organization.name,
#             "organization_type": teacher.organization.type,
#             "organization_position": teacher.organization.position,
#         }
#
#         return profile_data
#
# async def get_profile(self, session: AsyncSession, user_id: int, bucket_name: str) -> dict:
#     try:
#         result = await session.execute(
#             select(User).where(User.id == user_id)
#         )
#         user = result.scalars().first()
#
#         if not user:
#             raise HTTPException(status_code=404, detail="유저를 찾을 수 없습니다.")
#
#         profile_image_url = get_s3_url(bucket_name, user.profile_image)
#
#         profile_data = {
#             "id": user.id,
#             "role": user.role,
#             "nickname": user.tag.nickname if user.tag else None,
#             "profile_image": profile_image_url,
#         }
#
#         if user.role == "student":
#             student_data = await self.get_student_profile(session, user_id)
#             profile_data.update(student_data)
#         elif user.role == "teacher":
#             teacher_data = await self.get_teacher_profile(session, user_id)
#             profile_data.update(teacher_data)
#
#         posts_result = await session.execute(
#             select(Post).where(Post.author_id == user_id)
#         )
#         posts = posts_result.scalars().all()
#
#         posts_data = {
#             "post_count": len(posts),
#             "like_count": sum(post.like_count for post in posts),
#             "comment_count": sum(post.comment_count for post in posts),
#             "posts": [
#                 {
#                     "post_id": post.external_id,
#                     "post_image": get_s3_url(bucket_name, post.images[0].image_path) if post.images else None,
#                 }
#                 for post in posts
#             ],
#         }
#
#         profile_data.update(posts_data)
#
#         return profile_data
#
#     except Exception as e:
#         logger.error(f"Error fetching profile for user_id={user_id}: {e}")
#         raise HTTPException(status_code=500, detail="프로필 조회 중 오류가 발생했습니다.")
