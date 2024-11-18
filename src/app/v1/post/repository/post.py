from ulid import ulid  # type: ignore

from src.app.v1.post.entity.post import Post
from src.app.v1.post.schema.post import PostCreateRequest
from src.config.database.postgresql import SessionLocal


class PostRepository:
    @staticmethod
    async def create_post(user_id: str, post_id: ulid, post: PostCreateRequest):
        raise NotImplementedError

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
