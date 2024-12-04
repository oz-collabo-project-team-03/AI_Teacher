from datetime import datetime
from typing import List

from pydantic import BaseModel


class CommentCreateResponse(BaseModel):
    comment_id: int
    post_id: int
    author_id: int
    author_nickname: str
    content: str
    created_at: datetime
    tags: List[str] = []
    parent_comment_id: int | None = None
    recomment_count: int = 0


class CommentResponse(BaseModel):
    comment_id: int
    post_id: int
    author_id: int
    author_nickname: str
    profile_image: str | None = None
    content: str
    created_at: datetime
    tags: List[str] = []
    parent_comment_id: int | None = None
    recomment_count: int = 0
    children: List["CommentResponse"] = []


class CommentListResponse(BaseModel):
    comments: List[CommentResponse]
    total_count: int
