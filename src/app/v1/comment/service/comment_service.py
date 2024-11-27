from collections import defaultdict

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.app.common.models.tag import Tag
from src.app.v1.comment.entity.comment import Comment
from src.app.v1.comment.entity.comment_tag import CommentTag
from src.app.v1.user.entity.user import User


class CommentService:
    async def create_comment_with_tags(
        self, session: AsyncSession, post_id: int, author_id: int, content: str, tag_nicknames: list[str] | None
    ) -> Comment:
        async with session.begin():
            comment = Comment(post_id=post_id, author_id=author_id, content=content)
            session.add(comment)
            await session.flush()

            if not tag_nicknames:
                return comment

            tag_query = select(Tag).where(Tag.nickname.in_(tag_nicknames))
            tags_result = await session.execute(tag_query)
            tags = tags_result.scalars().all()

            invalid_tags = set(tag_nicknames) - {tag.nickname for tag in tags}
            if invalid_tags:
                raise ValueError(f"유효하지 않은 태그입니다: {', '.join(invalid_tags)}")

            comment_tags = [CommentTag(comment_id=comment.id, tag_id=tag.id) for tag in tags]
            session.add_all(comment_tags)

        return comment

    async def get_comments_with_tags(self, session: AsyncSession, post_id: int):
        comment_query = (
            select(
                Comment.id,
                Comment.post_id,
                Comment.author_id,
                Comment.content,
                Comment.created_at,
                Tag.nickname.label("author_nickname"),
            )
            .join(User, Comment.author_id == User.id)
            .join(Tag, User.id == Tag.user_id)
            .where(Comment.post_id == post_id)
        )
        comment_result = await session.execute(comment_query)
        comments = comment_result.fetchall()
        if not comments:
            return []

        comment_ids = [comment.id for comment in comments]
        tag_query = select(CommentTag.comment_id, Tag.nickname).join(Tag, CommentTag.tag_id == Tag.id).where(CommentTag.comment_id.in_(comment_ids))
        tag_result = await session.execute(tag_query)

        tag_map = defaultdict(list)
        for comment_id, nickname in tag_result:
            tag_map[comment_id].append(nickname)

        return [
            {
                "comment_id": comment.id,
                "post_id": comment.post_id,
                "author_id": comment.author_id,
                "author_nickname": comment.author_nickname,
                "content": comment.content,
                "tags": tag_map.get(comment.id, []),
                "created_at": comment.created_at,
            }
            for comment in comments
        ]

    async def delete_comment(self, session: AsyncSession, comment_id: int, user_id: int):
        async with session.begin():
            query = select(Comment).where(Comment.id == comment_id)
            result = await session.execute(query)
            comment = result.scalars().first()

            if not comment:
                raise ValueError("댓글을 찾을 수 없습니다.")

            if comment.author_id != user_id:
                raise HTTPException(status_code=403, detail="해당 댓글의 작성자가 아닙니다.")

            await session.delete(comment)
