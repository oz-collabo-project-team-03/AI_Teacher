from datetime import datetime
from typing import List

from pydantic import BaseModel


class CommentResponse(BaseModel):
    comment_id: int
    post_id: int
    author_id: int
    author_nickname: str
    content: str
    created_at: datetime
    tags: List[str] = []


class CommentListResponse(BaseModel):
    comments: List[CommentResponse]
    total_count: int
