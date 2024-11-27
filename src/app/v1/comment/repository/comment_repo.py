from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.app.common.models.tag import Tag
from src.app.v1.comment.entity.comment import Comment
from src.app.v1.comment.entity.comment_tag import CommentTag


class CommentRepository:
    async def create_comment(self, session: AsyncSession, comment: Comment, tags: list[str] | None):
        async with session.begin():
            session.add(comment)
            await session.flush()

            if tags:
                tag_query = select(Tag).where(Tag.nickname.in_(tags))
                tag_result = await session.execute(tag_query)
                tag_objects = tag_result.scalars().all()

                comment_tags = [CommentTag(comment_id=comment.id, tag_id=tag.id) for tag in tag_objects]
                session.add_all(comment_tags)

            await session.commit()
        return comment

    async def get_comments_by_post_id(self, session: AsyncSession, post_id: int):
        query = select(Comment).where(Comment.post_id == post_id)
        result = await session.execute(query)
        return result.scalars().all()

    async def delete_comment(self, session: AsyncSession, comment_id: int):
        query = select(Comment).where(Comment.id == comment_id)
        result = await session.execute(query)
        comment = result.scalars().first()
        if not comment:
            return None

        async with session.begin():
            await session.delete(comment)
        return comment
