from fastapi import File
from ulid import ulid  # type: ignore

from src.app.v1.post.repository.post import PostRepository
from src.app.v1.post.schema.post import PostCreateRequest, PostUpdateRequest


class PostService:
    def __init__(self):
        self.post_repository = PostRepository()

    def create_post(self, user_id: str, post: PostCreateRequest):
        return self.post_repository.create_post(user_id=user_id, post_id=ulid(), post=post)

    def get_post(self, post_id: str):
        return self.post_repository.get_post(post_id=post_id)

    def update_post(self, user_id: str, post_id: str, post: PostUpdateRequest):
        return self.post_repository.update_post(user_id=user_id, post_id=post_id, post=post)

    def delete_post(self, user_id: str, post_id: str):
        return self.post_repository.delete_post(user_id=user_id, post_id=post_id)
