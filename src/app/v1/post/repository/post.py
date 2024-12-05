# type: ignore
import os

from dotenv import load_dotenv
from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import joinedload
from starlette import status
from ulid import ulid  # type: ignore

from src.app.v1.user.entity.study_group import StudyGroup
from src.app.common.models.image import Image
from src.app.common.models.tag import Tag
from src.app.common.utils.consts import UserRole
from src.app.v1.post.entity.post import Post
from src.app.v1.post.entity.post_image import PostImage
from src.app.v1.post.entity.post_like import PostLike
from src.app.v1.post.schema.post import PostCreateRequest, PostUpdateRequest
from src.app.v1.user.entity.student import Student
from src.app.v1.user.entity.teacher import Teacher
from src.app.v1.user.entity.user import User
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

            return {"post_id": new_post.external_id}

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
                image_paths[idx] = img.image_path if img else None  # type: ignore

            # 선생님 정보 조회 (is_with_teacher가 True인 경우)
            teacher_info = None
            if post.is_with_teacher:
                teacher_query = (
                    select(User)
                    .options(joinedload(User.tag))  # Tag 정보를 즉시 로딩
                    .join(StudyGroup, StudyGroup.teacher_id == User.id)  # StudyGroup 테이블과 조인
                    .where(StudyGroup.student_id == student.id)  # 현재 학생의 ID로 필터링
                    .limit(1)
                )
                teacher_result = await session.execute(teacher_query)
                teacher = teacher_result.unique().scalar_one_or_none()
                if teacher:
                    teacher_info = {
                        "nickname": teacher.tag.nickname if teacher.tag else None,
                        "profile_image": teacher.profile_image,
                        "user_id": teacher.id,
                    }

            response = {
                "nickname": user.tag.nickname if user.tag else None,
                "user_id": teacher.id,
                "profile_image": user.profile_image,
                "career_aspiration": student.career_aspiration,
                "interest": student.interest,
                "like_count": post.like_count,
                "comment_count": post.comment_count,
                "post_id": post.external_id,
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
    async def update_post(user_id: str, post_id: str, post: PostUpdateRequest):
        async with SessionLocal() as session:
            # 게시글 조회
            query = select(Post).where(Post.external_id == post_id)
            result = await session.execute(query)
            existing_post = result.scalar_one_or_none()

            if not existing_post:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

            # 작성자 권한 확인
            if str(existing_post.author_id) != str(user_id):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have permission to update this post")

            try:
                # 게시글 업데이트
                existing_post.content = post.content
                existing_post.is_with_teacher = post.is_with_teacher

                # 새 이미지 목록에서 None이 아닌 것만 필터링
                new_images = [img for img in [post.image1, post.image2, post.image3] if img is not None]

                if new_images:  # 새로운 이미지가 있는 경우에만 이미지 업데이트 수행
                    # 기존 이미지 정보 조회 및 삭제
                    old_images_query = select(PostImage).where(PostImage.post_id == existing_post.id)
                    old_images_result = await session.execute(old_images_query)
                    old_images = old_images_result.scalars().all()

                    for old_image in old_images:
                        await session.delete(old_image)

                    # 새 이미지 추가
                    for image_url in new_images:
                        # Image 테이블에 새 이미지 추가
                        new_image = Image(image_path=image_url)
                        session.add(new_image)
                        await session.flush()

                        # PostImage 테이블에 연결 정보 추가
                        post_image = PostImage(post_id=existing_post.id, image_id=new_image.id)
                        session.add(post_image)

                await session.commit()

            except Exception as e:
                await session.rollback()
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @staticmethod
    async def delete_post(user_id: str, post_id: str):
        async with SessionLocal() as session:
            try:
                # 게시글 조회
                query = select(Post).where(Post.external_id == post_id)
                result = await session.execute(query)
                post = result.scalar_one_or_none()

                if not post:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

                # 작성자 권한 확인
                if str(post.author_id) != str(user_id):
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have permission to delete this post")

                # 게시글에 연결된 이미지 관계 삭제
                await session.execute(delete(PostImage).where(PostImage.post_id == post.id))
                await session.flush()

                # 게시글 삭제
                await session.execute(delete(Post).where(Post.id == post.id))

                await session.commit()

            except HTTPException:
                await session.rollback()
                raise
            except Exception as e:
                await session.rollback()
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @staticmethod
    async def like_post(user_id: str, post_id: str):
        async with SessionLocal() as session:
            try:
                # post 존재 여부 확인
                post_query = select(Post).where(Post.external_id == post_id)
                post_result = await session.execute(post_query)
                post = post_result.scalar_one_or_none()

                if not post:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

                # 이미 좋아요 했는지 확인
                existing_like = await session.execute(select(PostLike).where(PostLike.user_id == int(user_id), PostLike.post_id == post.id))
                if existing_like.scalar_one_or_none():
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already liked this post")

                # 좋아요 추가
                new_like = PostLike(user_id=int(user_id), post_id=post.id)
                session.add(new_like)

                # 게시글의 좋아요 수 증가
                post.like_count += 1

                await session.commit()

            except HTTPException:
                await session.rollback()
                raise
            except Exception as e:
                await session.rollback()
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @staticmethod
    async def unlike_post(user_id: str, post_id: str):
        async with SessionLocal() as session:
            try:
                # post 존재 여부 확인
                post_query = select(Post).where(Post.external_id == post_id)
                post_result = await session.execute(post_query)
                post = post_result.scalar_one_or_none()

                if not post:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

                # 좋아요 레코드 찾기
                like_query = select(PostLike).where(PostLike.user_id == int(user_id), PostLike.post_id == post.id)
                like_result = await session.execute(like_query)
                like = like_result.scalar_one_or_none()

                if not like:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Haven't liked this post yet")

                # 좋아요 삭제
                await session.delete(like)

                # 게시글의 좋아요 수 감소
                post.like_count = max(0, post.like_count - 1)  # 음수 방지

                await session.commit()

            except HTTPException:
                await session.rollback()
                raise
            except Exception as e:
                await session.rollback()
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @staticmethod
    async def get_posts(page: int):
        PAGE_SIZE = 10

        async with SessionLocal() as session:
            # 전체 게시글 수 조회
            total_count_query = select(func.count(Post.id))
            total_count_result = await session.execute(total_count_query)
            total_count = total_count_result.scalar()

            # 메인 쿼리 - 모든 필요한 관계를 한 번에 로드
            query = (
                select(Post, User, Student, Tag)
                .join(User, Post.author_id == User.id)
                .join(Student, User.id == Student.user_id)
                .join(Tag, User.id == Tag.user_id)
                .order_by(Post.created_at.desc())
                .offset((page - 1) * PAGE_SIZE)
                .limit(PAGE_SIZE)
            )

            result = await session.execute(query)
            rows = result.all()

            posts = []
            for row in rows:
                post, user, student, tag = row

                # 이미지 조회
                images_query = (
                    select(Image.image_path)
                    .join(PostImage, Image.id == PostImage.image_id)
                    .where(PostImage.post_id == post.id)
                    .order_by(PostImage.id)
                    .limit(3)
                )
                images_result = await session.execute(images_query)
                image_paths = [path[0] for path in images_result]

                # 3개까지 채우기
                while len(image_paths) < 3:
                    image_paths.append(None)

                # 선생님 정보 조회 (is_with_teacher가 True인 경우)
                teacher_info = None
                if post.is_with_teacher:
                    teacher_query = (
                        select(User)
                        .options(joinedload(User.tag))  # Tag 정보를 즉시 로딩
                        .join(StudyGroup, StudyGroup.teacher_id == User.id)  # StudyGroup 테이블과 조인
                        .where(StudyGroup.student_id == student.id)  # 현재 학생의 ID로 필터링
                        .limit(1)
                    )
                    teacher_result = await session.execute(teacher_query)
                    teacher = teacher_result.unique().scalar_one_or_none()
                    if teacher:
                        teacher_info = {
                            "nickname": teacher.tag.nickname if teacher.tag else None,
                            "user_id": teacher.id,
                            "profile_image": teacher.profile_image,
                        }

                post_data = {
                    "nickname": tag.nickname,
                    "user_id": teacher.id,
                    "profile_image": user.profile_image,
                    "career_aspiration": student.career_aspiration,
                    "interest": student.interest,
                    "like_count": post.like_count,
                    "comment_count": post.comment_count,
                    "post_id": post.external_id,
                    "image1": image_paths[0],
                    "image2": image_paths[1],
                    "image3": image_paths[2],
                    "content": post.content,
                    "created_at": post.created_at.isoformat(),
                }

                if teacher_info:
                    post_data["teacher"] = teacher_info

                posts.append(post_data)

            load_dotenv()

            host = os.getenv("HOST", "127.0.0.1:8000")

            base_url = f"http://{host}/posts"

            # 페이지네이션 정보
            next_page = f"{base_url}?page={page + 1}"
            previous_page = f"{base_url}?page={page - 1}" if page > 1 else None

            return {"next": next_page, "previous": previous_page, "posts": posts}

    @staticmethod
    async def get_user_posts(user_id: str, page: int):
        PAGE_SIZE = 10

        async with SessionLocal() as session:
            # 전체 게시글 수 조회 (해당 사용자의)
            user_query = select(User.id).where(User.id == int(user_id))
            user_result = await session.execute(user_query)
            internal_user_id = user_result.scalar_one_or_none()

            if not internal_user_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

            # 전체 게시글 수 조회 (해당 사용자의)
            total_count_query = select(func.count(Post.id)).where(Post.author_id == internal_user_id)
            total_count_result = await session.execute(total_count_query)
            total_count = total_count_result.scalar()

            # 메인 쿼리 - 사용자의 게시글만 필터링
            query = (
                select(Post, User, Student, Tag)
                .join(User, Post.author_id == User.id)
                .join(Student, User.id == Student.user_id)
                .join(Tag, User.id == Tag.user_id)
                .where(Post.author_id == internal_user_id)  # internal id로 필터링
                .order_by(Post.created_at.desc())
                .offset((page - 1) * PAGE_SIZE)
                .limit(PAGE_SIZE)
            )

            result = await session.execute(query)
            rows = result.all()

            posts = []
            for row in rows:
                post, user, student, tag = row

                # 이미지 조회
                images_query = (
                    select(Image.image_path)
                    .join(PostImage, Image.id == PostImage.image_id)
                    .where(PostImage.post_id == post.id)
                    .order_by(PostImage.id)
                    .limit(3)
                )
                images_result = await session.execute(images_query)
                image_paths = [path[0] for path in images_result]

                # 3개까지 채우기
                while len(image_paths) < 3:
                    image_paths.append(None)

                # 선생님 정보 조회 (is_with_teacher가 True인 경우)
                teacher_info = None
                if post.is_with_teacher:
                    teacher_query = (
                        select(User)
                        .options(joinedload(User.tag))  # Tag 정보를 즉시 로딩
                        .join(StudyGroup, StudyGroup.teacher_id == User.id)  # StudyGroup 테이블과 조인
                        .where(StudyGroup.student_id == student.id)  # 현재 학생의 ID로 필터링
                        .limit(1)
                    )
                    teacher_result = await session.execute(teacher_query)
                    teacher = teacher_result.unique().scalar_one_or_none()
                    if teacher:
                        teacher_info = {
                            "nickname": teacher.tag.nickname if teacher.tag else None,
                            "user_id": teacher.id,
                            "profile_image": teacher.profile_image,
                        }

                post_data = {
                    "nickname": tag.nickname,
                    "user_id": teacher.id,
                    "profile_image": user.profile_image,
                    "career_aspiration": student.career_aspiration,
                    "interest": student.interest,
                    "like_count": post.like_count,
                    "comment_count": post.comment_count,
                    "post_id": post.external_id,
                    "image1": image_paths[0],
                    "image2": image_paths[1],
                    "image3": image_paths[2],
                    "content": post.content,
                    "created_at": post.created_at.isoformat(),
                }

                if teacher_info:
                    post_data["teacher"] = teacher_info

                posts.append(post_data)

            load_dotenv()
            host = os.getenv("HOST", "127.0.0.1:8000")
            base_url = f"http://{host}/posts/me"

            # 페이지네이션 정보
            next_page = f"{base_url}?page={page + 1}" if (page * PAGE_SIZE) < total_count else None
            previous_page = f"{base_url}?page={page - 1}" if page > 1 else None

            return {"next": next_page, "previous": previous_page, "posts": posts}
