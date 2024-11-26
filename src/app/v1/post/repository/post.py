from ulid import ulid  # type: ignore

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
        raise NotImplementedError

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
