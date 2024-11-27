from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.common.models.tag import Tag
from src.app.common.utils.dependency import get_current_user, get_session
from src.app.v1.comment.schema.requestDto import CommentCreateRequest
from src.app.v1.comment.schema.responseDto import CommentListResponse, CommentResponse
from src.app.v1.comment.service.comment_service import CommentService

router = APIRouter(prefix="/comments", tags=["Comments"])
comment_service = CommentService()


@router.post("/write/{post_id}", response_model=CommentResponse)
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
            author_id=int(current_user["user_id"]),  # 정수형 변환 추가
            content=payload.content,
            tag_nicknames=payload.tags,
        )

        # 작성자의 닉네임 조회
        author_query = select(Tag.nickname).where(Tag.user_id == int(current_user["user_id"]))  # 정수형 변환 추가
        author_result = await session.execute(author_query)
        author_nickname = author_result.scalar() or "Anonymous"

        return CommentResponse(
            comment_id=comment.id,
            post_id=comment.post_id,
            author_id=comment.author_id,
            author_nickname=author_nickname,
            content=comment.content,
            created_at=comment.created_at,
            tags=payload.tags or [],
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
