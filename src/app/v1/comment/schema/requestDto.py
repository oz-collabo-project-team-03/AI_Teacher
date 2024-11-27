from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class CommentCreateRequest(BaseModel):
    content: str = Field(..., max_length=300, description="댓글 내용")
    tags: List[str] | None = Field(None, description="태그된 사용자 닉네임 리스트")