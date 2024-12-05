import logging
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload, selectinload
from ulid import ulid  # type: ignore

from src.app.common.models.tag import Tag
from src.app.common.models.image import Image
from src.app.common.utils.consts import UserRole
from src.app.common.utils.verify_password import (
    hash_password,
)
from src.app.v1.post.entity.post import Post
from src.app.v1.post.entity.post_image import PostImage
from src.app.v1.user.entity.organization import Organization
from src.app.v1.user.entity.student import Student
from src.app.v1.user.entity.study_group import StudyGroup
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
                if not hasattr(User, key):
                    logger.error(f"Invalid field in query parameters: {key}")
                    raise HTTPException(status_code=400, detail=f"Invalid field '{key}' in query parameters.")

                # 필드 값 변환 처리 (예: id는 정수로 변환)
                if key == "id":
                    try:
                        value = int(value)
                    except ValueError:
                        logger.error(f"Invalid value for 'id': {value}")
                        raise HTTPException(status_code=400, detail="Invalid value for 'id'.")

                query = query.filter(getattr(User, key) == value)

            logger.debug(f"Generated query: {query}")
            result = await session.execute(query)
            user = result.scalars().first()

            if not user:
                logger.warning(f"No user found for query: {kwargs}")
                return None

            logger.debug(f"Query result: {user}")
            return user

        except HTTPException as e:
            print(f"HTTPException 발생: {e.status_code}, {e.detail}")
            raise e

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
                if nickname := user_data.get("nickname"):
                    existing_nickname = await session.execute(select(Tag).where(Tag.nickname == nickname))
                    if existing_nickname.scalar():
                        raise HTTPException(status_code=400, detail="중복된 닉네임이 존재합니다.")

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
                await session.rollback()
                print(f"IntegrityError 발생: {e}")
                error_detail = str(e.orig).lower()

                if "email" in error_detail:
                    detail = "중복된 이메일이 존재합니다."
                elif "phone" in error_detail:
                    detail = "중복된 전화번호가 존재합니다."
                elif "nickname" in error_detail:
                    detail = "중복된 닉네임이 존재합니다."
                else:
                    detail = "중복된 데이터가 감지되었습니다."

                print(f"400 에러 반환: {detail}")
                raise HTTPException(status_code=400, detail=detail)

    async def create_teacher(self, session: AsyncSession, user_data: dict, teacher_data: dict):
        async with session.begin():
            try:
                if nickname := user_data.get("nickname"):
                    existing_nickname = await session.execute(select(Tag).where(Tag.nickname == nickname))
                    if existing_nickname.scalar():
                        raise HTTPException(status_code=400, detail="중복된 닉네임이 존재합니다.")

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

    async def reset_user_password(self, session: AsyncSession, email: str, temp_password: str):
        async with session.begin():

            user = await self.get_user_by_email(session, email)
            if not user:
                raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

            user.password = hash_password(temp_password)
            logger.info(f"사용자 비밀번호 업데이트 완료. email: {email}")

    # 모든 선생님 (이름, 조직이름, 조직타입, 포지션) 조회
    async def get_all_teachers_info(self, session: AsyncSession) -> list[dict]:
        query = (
            select(
                Teacher.id.label("teacher_id"),
                Tag.nickname.label("name"),
                Organization.name.label("organization_name"),
                Organization.type.label("organization_type"),
                Organization.position.label("position"),
            )
            .join(User, User.id == Teacher.user_id)  #
            .join(Organization, Organization.teacher_id == Teacher.id, isouter=True)
            .join(Tag, Tag.user_id == User.id, isouter=True)
            .where(User.role == UserRole.TEACHER)
        )

        result = await session.execute(query)
        teachers = result.fetchall()

        return [
            {
                "teacher_id": teacher.teacher_id,
                "name": teacher.name,
                "organization_name": teacher.organization_name,
                "organization_type": teacher.organization_type,
                "position": teacher.position,
            }
            for teacher in teachers
        ]

    # 학생 최초 로그인 시 선생님 조회
    async def get_student_id(self, session: AsyncSession, user_id: int) -> int | None:
        query = select(Student.id).where(Student.user_id == user_id)
        result = await session.execute(query)
        return result.scalar()

    async def get_teacher_by_id_and_name(self, session: AsyncSession, teacher_id: int, name: str) -> int | None:
        query = select(Teacher.id).join(Tag, Tag.user_id == Teacher.user_id).where(Teacher.id == teacher_id).where(Tag.nickname == name)
        result = await session.execute(query)
        return result.scalar()

    async def create_study_group(self, session: AsyncSession, student_id: int, teacher_id: int):
        new_group = StudyGroup(student_id=student_id, teacher_id=teacher_id)
        session.add(new_group)
        await session.commit()
        return new_group

    # 교사 회원정보 조회 -> 이메일, 패스워드, 전화번호
    async def get_teacher_info(self, session: AsyncSession, user_id: int) -> dict:
        user = await self.get_user_by_id(session, user_id)
        if not user or user.role != UserRole.TEACHER:
            logger.error(f"교사 정보를 찾을 수 없습니다: user_id={user_id}")
            raise HTTPException(status_code=404, detail="교사 정보를 찾을 수 없습니다.")

        teacher_info = {
            "password": user.password,
            "phone": user.phone,
        }
        logger.info(f"교사 정보 조회 성공: user_id={user_id}, teacher_info={teacher_info}")
        return teacher_info

    async def get_student_info(self, session: AsyncSession, user_id: int) -> dict:
        user = await self.get_user_by_id(session, user_id)
        if not user or user.role != UserRole.STUDENT:
            logger.error(f"학생 정보를 찾을 수 없습니다: user_id={user_id}")
            raise HTTPException(status_code=404, detail="학생 정보를 찾을 수 없습니다.")

        student = user.student
        if not student:
            logger.error(f"학생 데이터를 찾을 수 없습니다: user_id={user_id}")
            raise HTTPException(status_code=404, detail="학생 데이터를 찾을 수 없습니다.")

        student_info = {
            "password": user.password,
            "phone": user.phone,
            "school": student.school,
            "grade": student.grade,
        }
        logger.info(f"학생 정보 조회 성공: user_id={user_id}, student_info={student_info}")
        return student_info

    async def update_teacher_info(self, session: AsyncSession, user_id: int, update_data: dict):
        async with session.begin():
            user = await self.get_user_by_id(session, user_id)
            if not user or user.role != UserRole.TEACHER:
                logger.error(f"교사 정보를 찾을 수 없습니다: user_id={user_id}")
                raise HTTPException(status_code=404, detail="교사 정보를 찾을 수 없습니다.")

            for field, value in update_data.items():
                setattr(user, field, value)

    async def update_student_info(self, session: AsyncSession, user_id: int, common_fields: dict, student_fields: dict):
        async with session.begin():
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

    # 프로필 조회
    async def get_user_with_profile(self, user_id: int, session: AsyncSession):
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
        user = result.scalars().first()
        if not user:
            logger.warning(f"User with ID {user_id} not found.")
        return user

    async def get_posts_by_user(self, user_id: int, session: AsyncSession):
        try:
            query = (
                select(Post.external_id, Post, Image.image_path)
                .join(PostImage, PostImage.post_id == Post.id, isouter=True)
                .join(Image, Image.id == PostImage.image_id, isouter=True)  # Image와 조인 추가
                .where(Post.author_id == user_id)
            )
            result = await session.execute(query)
            rows = result.fetchall()

            posts = {}
            for external_id, post, image_path in rows:
                if post.id not in posts:
                    posts[post.id] = {
                        "external_id": external_id,
                        "post": post,
                        "images": [],
                    }
                if image_path:
                    posts[post.id]["images"].append(image_path)

            logger.info(f"Retrieved {len(posts)} posts for user ID {user_id}")
            return posts
            # return list(posts.values())
        except Exception as e:
            logger.error(f"Error fetching posts for user ID {user_id}: {str(e)}")
            raise

    # 학생 프로필 업데이트
    async def update_student_profile(self, user_id: int, update_data: dict, session: AsyncSession) -> bool:
        user = await self.get_user_with_profile(user_id, session)
        if not user:
            logger.warning(f"User with ID {user_id} not found.")
            raise HTTPException(status_code=404, detail="유저를 찾을 수 없습니다.")

        if "nickname" in update_data:
            if user.tag:
                user.tag.nickname = update_data["nickname"]
            else:
                new_tag = Tag(user_id=user.id, nickname=update_data["nickname"])
                session.add(new_tag)

        if "profile_image" in update_data:
            user.profile_image = update_data["profile_image_url"]

        if user.student:
            student = user.student
            if "career_aspiration" in update_data:
                student.career_aspiration = update_data["career_aspiration"]
            if "interest" in update_data:
                student.interest = update_data["interest"]
            if "description" in update_data:
                student.description = update_data["description"]

        logger.info(f"User profile updated successfully for user_id={user_id}")
        return True

    # 교사 프로필 변경
    async def update_teacher_profile(self, user_id: int, profile_data: dict, session: AsyncSession) -> bool:
        user = await self.get_user_with_profile(user_id, session)
        if not user:
            print(f"User with ID {user_id} not found.")
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

        if "nickname" in profile_data:
            if user.tag:
                user.tag.nickname = profile_data["nickname"]
            else:
                new_tag = Tag(user_id=user.id, nickname=profile_data["nickname"])
                session.add(new_tag)

        if "profile_image" in profile_data:
            user.profile_image = profile_data["profile_image_url"]

        if user.teacher and user.teacher.organization:
            organization = user.teacher.organization
            if "organization_name" in profile_data:
                organization.name = profile_data["organization_name"]
            if "organization_type" in profile_data:
                organization.type = profile_data["organization_type"]
            if "organization_position" in profile_data:
                organization.position = profile_data["organization_position"]

        await session.flush()
        print(f"Teacher profile updated successfully for user_id={user_id}")
        return True
