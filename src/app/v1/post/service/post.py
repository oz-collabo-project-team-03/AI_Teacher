from ulid import ulid

from src.app.v1.post.repository.post import PostRepository
from src.app.v1.post.schema.post import PostCreateRequest


class PostService:
    def __init__(self):
        self.post_repository = PostRepository()

    def create_post(self, user_id: str, post: PostCreateRequest):
        return self.post_repository.create_post(user_id=user_id, post_id=ulid(), post=post)
