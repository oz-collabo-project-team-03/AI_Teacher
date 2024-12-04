from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.app.common.models.tag import Tag
from src.app.v1.comment.entity.comment import Comment
from src.app.v1.comment.entity.comment_tag import CommentTag


class CommentRepository:
    async def create_comment(self, session: AsyncSession, comment: Comment, tags: list[Tag]):
        session.add(comment)
        await session.flush()
        comment_tags = [CommentTag(comment_id=comment.id, tag_id=tag.id) for tag in tags]
        session.add_all(comment_tags)

    async def get_comments_by_post_id(self, session: AsyncSession, post_id: int):
        query = (
            select(
                Comment,
                func.array_agg(Tag.nickname).label("tags"),  # 태그 닉네임들을 배열로 묶음
            )
            .join(CommentTag, Comment.id == CommentTag.comment_id, isouter=True)  # CommentTag와 JOIN
            .join(Tag, CommentTag.tag_id == Tag.id, isouter=True)  # Tag와 JOIN
            .where(Comment.post_id == post_id)
            .group_by(Comment.id)  # Comment 별로 태그를 그룹화
            .order_by(Comment.created_at)
        )

        result = await session.execute(query)
        return result.fetchall()

    async def delete_comment(self, session: AsyncSession, comment: Comment):
        await session.delete(comment)

    async def get_comment(self, session: AsyncSession, comment_id: int):
        query = select(Comment).where(Comment.id == comment_id)
        result = await session.execute(query)
        return result.scalars().first()

    async def get_valid_tags(self, session: AsyncSession, tag_nicknames: list[str]):
        query = select(Tag).where(Tag.nickname.in_(tag_nicknames))
        result = await session.execute(query)
        return result.scalars().all()

    async def get_user_info(self, session: AsyncSession, user_id: int) -> dict:
        from src.app.v1.user.entity.user import User
        query = (
            select(Tag.nickname, User.profile_image)
            .join(User, Tag.user_id == User.id)
            .where(Tag.user_id == user_id)
        )
        result = await session.execute(query)
        row = result.first()
        if row:
            return {"nickname": row.nickname, "profile_image": row.profile_image}
        return {"nickname": "Anonymous", "profile_image": None}
