from src.config.database.postgresql import SessionLocal
from src.app.v1.post.entity.post import Post


class PostRepository:
    @staticmethod
    async def create_post(post: Post):
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
