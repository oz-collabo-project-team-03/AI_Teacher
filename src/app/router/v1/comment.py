from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.common.utils.dependency import get_current_user, get_session
from src.app.v1.comment.schema.requestDto import CommentCreateRequest
from src.app.v1.comment.schema.responseDto import (
    CommentCreateResponse,
    CommentListResponse,
    CommentResponse,
)
from src.app.v1.comment.service.comment_service import CommentService

router = APIRouter(prefix="/comments", tags=["Comments"])
comment_service = CommentService()


@router.post("/write/{post_id}", response_model=CommentCreateResponse)
async def create_comment(
    post_id: int,
    payload: CommentCreateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    try:
        # 댓글 생성
        comment = await comment_service.create_comment_with_tags(
            session=session,
            post_id=post_id,
            author_id=int(current_user["user_id"]),
            content=payload.content,
            tag_nicknames=payload.tags,
            parent_comment_id=payload.parent_comment_id,
        )
        # 부모 댓글의 대댓글 개수 확인
        recomment_count = 0
        if payload.parent_comment_id:
            recomment_count = await comment_service.get_recomment_count(session, payload.parent_comment_id)

        # 닉네임 조회
        author_nickname = await comment_service.get_user_nickname(session, int(current_user["user_id"]))

        return CommentResponse(
            comment_id=comment.id,
            post_id=comment.post_id,
            author_id=comment.author_id,
            author_nickname=author_nickname,
            content=comment.content,
            created_at=comment.created_at,
            tags=payload.tags or [],
            parent_comment_id=comment.parent_comment_id,
            recomment_count=recomment_count,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{post_id}", response_model=CommentListResponse)
async def get_comments(post_id: int, session: AsyncSession = Depends(get_session)):
    comments = await comment_service.get_comments_with_tags(session, post_id)
    return {"comments": comments, "total_count": len(comments)}


@router.delete("/{comment_id}", status_code=204)
async def delete_comment(comment_id: int, session: AsyncSession = Depends(get_session), current_user: dict = Depends(get_current_user)):
    try:
        await comment_service.delete_comment(session, comment_id, int(current_user["user_id"]))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
