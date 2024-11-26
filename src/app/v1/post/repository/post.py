from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from ulid import ulid  # type: ignore

from src.app.common.utils.consts import UserRole
from src.app.v1.user.entity.student import Student
from src.app.v1.user.entity.teacher import Teacher
from src.app.v1.user.entity.user import User
from src.app.common.models.image import Image
from src.app.v1.post.entity.post import Post
from src.app.v1.post.entity.post_image import PostImage
from src.app.v1.post.schema.post import PostCreateRequest
from src.config.database.postgresql import SessionLocal


class PostRepository:
    @staticmethod
    async def create_post(user_id: str, post_id: ulid, post: PostCreateRequest):
        async with SessionLocal() as session:
            new_post = Post(
                external_id=str(post_id),
                author_id=int(user_id),
                content=post.content,
                is_with_teacher=post.is_with_teacher,
            )

            session.add(new_post)
            await session.flush()

            image_paths = [post.image1]
            if post.image2:
                image_paths.append(post.image2)
            if post.image3:
                image_paths.append(post.image3)

            for idx, image_path in enumerate(image_paths, start=1):
                if image_path:
                    new_image = Image(image_path=image_path)
                    session.add(new_image)
                    await session.flush()

                    post_image = PostImage(image_id=new_image.id, post_id=new_post.id)
                    session.add(post_image)

            await session.commit()
            await session.refresh(new_post)

            return new_post

    @staticmethod
    async def get_post(post_id: str):
        async with SessionLocal() as session:
            # 게시글과 관련 정보를 조회하는 쿼리
            query = (
                select(Post, User, Student)
                .options(joinedload(User.tag))  # Tag 정보를 즉시 로딩
                .join(User, Post.author_id == User.id)
                .join(Student, User.id == Student.user_id)
                .where(Post.external_id == post_id)
            )

            result = await session.execute(query)
            row = result.unique().first()

            if not row:
                raise HTTPException(status_code=404, detail="Post not found")

            post, user, student = row

            # 이미지 조회를 위한 별도 쿼리
            image_query = select(Image).join(PostImage, Image.id == PostImage.image_id).where(PostImage.post_id == post.id).order_by(PostImage.id)
            image_result = await session.execute(image_query)
            images = image_result.scalars().all()

            # 이미지 URL 설정
            image_paths = [None, None, None]
            for idx, img in enumerate(images[:3]):
                image_paths[idx] = img.image_path if img else None

            # 선생님 정보 조회 (is_with_teacher가 True인 경우)
            teacher_info = None
            if post.is_with_teacher:
                teacher_query = (
                    select(User)
                    .options(joinedload(User.tag))  # Tag 정보를 즉시 로딩
                    .join(Teacher, User.id == Teacher.user_id)
                    .where(User.role == UserRole.TEACHER)
                    .limit(1)
                )
                teacher_result = await session.execute(teacher_query)
                teacher = teacher_result.unique().scalar_one_or_none()
                if teacher:
                    teacher_info = {"nickname": teacher.tag.nickname if teacher.tag else None, "profile_image": teacher.profile_image}

            response = {
                "nickname": user.tag.nickname if user.tag else None,
                "profile_image": user.profile_image,
                "career_aspiration": student.career_aspiration,
                "interest": student.interest,
                "like_count": post.like_count,
                "comment_count": post.comment_count,
                "image1": image_paths[0],
                "image2": image_paths[1],
                "image3": image_paths[2],
                "content": post.content,
                "created_at": post.created_at.isoformat(),
            }

            if teacher_info:
                response["teacher"] = teacher_info

            return response

    @staticmethod
    async def update_post(post_id: str, post: Post):
        raise NotImplementedError

    @staticmethod
    async def delete_post(post_id: str):
        raise NotImplementedError

    @staticmethod
    async def like_post(post_id: str, user_id: str):
        raise NotImplementedError

    @staticmethod
    async def unlike_post(post_id: str, user_id: str):
        raise NotImplementedError

    @staticmethod
    async def get_user_posts(user_id: str):
        raise NotImplementedError

    @staticmethod
    async def get_all_posts():
        raise NotImplementedError
