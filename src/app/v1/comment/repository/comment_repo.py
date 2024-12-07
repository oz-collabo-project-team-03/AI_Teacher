from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.app.common.models.tag import Tag
from src.app.v1.comment.entity.comment import Comment
from src.app.v1.comment.entity.comment_tag import CommentTag
from src.app.v1.post.entity.post import Post
from src.app.v1.user.entity.user import User


class CommentRepository:

    async def get_post_id_from_external_id(self, session: AsyncSession, external_id: str) -> int | None:
        """external_id로 실제 post_id를 조회"""
        query = select(Post.id).where(Post.external_id == external_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def create_comment(self, session: AsyncSession, comment: Comment, tags: list[Tag]):
        session.add(comment)
        await session.flush()
        comment_tags = [CommentTag(comment_id=comment.id, tag_id=tag.id) for tag in tags]
        session.add_all(comment_tags)

    async def get_comments_by_post_id(self, session: AsyncSession, post_id: int):
        query = (
            select(
                Comment,
                func.array_agg(Tag.nickname).label("tags"),
                User.external_id.label("user_external_id"),
                User.profile_image,
                Post.external_id.label("post_external_id"),  # Post의 external_id 추가
            )
            .join(CommentTag, Comment.id == CommentTag.comment_id, isouter=True)
            .join(Tag, CommentTag.tag_id == Tag.id, isouter=True)
            .join(User, Comment.author_id == User.id)
            .join(Post, Comment.post_id == Post.id)  # Post와 JOIN
            .where(Comment.post_id == post_id)
            .group_by(Comment.id, User.external_id, User.profile_image, Post.external_id)
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
        query = select(Tag.nickname, User.id, User.profile_image).join(Tag, Tag.user_id == User.id).where(User.id == user_id)
        result = await session.execute(query)
        row = result.first()
        if row:
            return {
                "id": row.id,  # User의 실제 id 반환
                "nickname": row.nickname,  # Tag 모델의 nickname 반환
                "profile_image": row.profile_image,
            }
        return {"id": None, "nickname": "Anonymous", "profile_image": None}

    async def increment_comment_count(self, session: AsyncSession, post_id: int, is_parent: bool):
        """댓글 생성 시 comment_count 증가 (대댓글 제외)"""
        if not is_parent:  # 대댓글은 카운트하지 않음
            return

        query = select(Post).where(Post.id == post_id)
        result = await session.execute(query)
        post = result.scalar_one_or_none()
        if post:
            post.comment_count += 1
            session.add(post)
            await session.flush()

    async def decrement_comment_count(self, session: AsyncSession, post_id: int, is_parent: bool):
        """댓글 삭제 시 comment_count 감소 (대댓글 제외)"""
        if not is_parent:  # 대댓글은 카운트하지 않음
            return

        query = select(Post).where(Post.id == post_id)
        result = await session.execute(query)
        post = result.scalar_one_or_none()
        if post and post.comment_count > 0:  # 음수 방지
            post.comment_count -= 1
            session.add(post)
            await session.flush()
