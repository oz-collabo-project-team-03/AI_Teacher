from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import aliased

from src.app.common.models.tag import Tag
from src.app.v1.comment.entity.comment import Comment
from src.app.v1.comment.entity.comment_tag import CommentTag



class CommentService:
    async def create_comment_with_tags(
        self, session: AsyncSession, post_id: int, author_id: int, content: str, tag_nicknames: list[str] | None, parent_comment_id: int | None
    ) -> Comment:
        async with session.begin():

            # parent_comment_id가 주어졌다면 해당 댓글이 존재하는지 확인
            if parent_comment_id:
                parent_query = select(Comment).where(Comment.id == parent_comment_id).with_for_update()
                parent_result = await session.execute(parent_query)
                parent_comment = parent_result.scalars().first()

                if not parent_comment:
                    raise ValueError("대댓글 대상 댓글을 찾을 수 없습니다.")
                if parent_comment.post_id != post_id:
                    raise ValueError("댓글은 동일한 게시글에만 대댓글로 작성할 수 있습니다.")

                parent_comment.recomment_count += 1
                session.add(parent_comment)

            # 새로운 댓글 생성
            comment = Comment(
                post_id=post_id,
                author_id=author_id,
                content=content,
                parent_comment_id=parent_comment_id,
            )
            session.add(comment)
            await session.flush()

            # 태그 처리
            if tag_nicknames:
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
        # 부모 댓글과 대댓글 테이블 구분
        ParentComment = Comment
        ChildComment = aliased(Comment)

        # 부모 댓글 가져오기
        parent_comment_query = select(
            ParentComment,
            func.count(ChildComment.id).label("child_count")
        ).outerjoin(
            ChildComment, ChildComment.parent_comment_id == ParentComment.id
        ).where(
            ParentComment.post_id == post_id, ParentComment.parent_comment_id == None
        ).group_by(
            ParentComment.id
        )

        parent_comments_result = await session.execute(parent_comment_query)
        parent_comments = parent_comments_result.all()

        if not parent_comments:
            return []  # 부모 댓글이 없으면 빈 리스트 반환

        # 부모 댓글 ID 리스트 생성
        parent_comment_ids = [comment[0].id for comment in parent_comments]

        # 대댓글 가져오기
        if parent_comment_ids:
            child_comment_query = select(Comment).where(Comment.parent_comment_id.in_(parent_comment_ids))
            child_comments_result = await session.execute(child_comment_query)
            child_comments = child_comments_result.scalars().all()
        else:
            child_comments = []

        # 태그 매핑
        tag_query = select(Tag.user_id, Tag.nickname)
        tag_result = await session.execute(tag_query)
        tag_map = {user_id: nickname for user_id, nickname in tag_result}

        # 결과 조합
        parent_comments_with_children = []
        for parent_comment, child_count in parent_comments:
            # 대댓글 필터링 및 데이터 구조화
            child_comments_for_parent = [
                {
                    "comment_id": child.id,
                    "post_id": child.post_id,
                    "author_id": child.author_id,
                    "author_nickname": tag_map.get(child.author_id, "Anonymous"),
                    "content": child.content,
                    "tags": [],
                    "created_at": child.created_at,
                    "parent_comment_id": child.parent_comment_id,
                }
                for child in child_comments if child.parent_comment_id == parent_comment.id
            ]

            # 부모 댓글 데이터 구조화
            parent_comments_with_children.append({
                "comment_id": parent_comment.id,
                "post_id": parent_comment.post_id,
                "author_id": parent_comment.author_id,
                "author_nickname": tag_map.get(parent_comment.author_id, "Anonymous"),
                "content": parent_comment.content,
                "tags": [],
                "created_at": parent_comment.created_at,
                "parent_comment_id": None,
                "recomment_count": child_count,
                "children": child_comments_for_parent,
            })

        return parent_comments_with_children

    async def delete_comment(self, session: AsyncSession, comment_id: int, user_id: int):
        async with session.begin():
            query = select(Comment).where(Comment.id == comment_id)
            result = await session.execute(query)
            comment = result.scalars().first()

            if not comment:
                raise ValueError("댓글을 찾을 수 없습니다.")

            if comment.author_id != user_id:
                raise HTTPException(status_code=403, detail="해당 댓글의 작성자가 아닙니다.")

            if comment.parent_comment_id:
                parent_query = select(Comment).where(Comment.id == comment.parent_comment_id)
                parent_result = await session.execute(parent_query)
                parent_comment = parent_result.scalars().first()
                if parent_comment:
                    parent_comment.recomment_count -= 1
                    session.add(parent_comment)

            await session.delete(comment)

    async def get_user_nickname(self, session: AsyncSession, user_id: int) -> str:
        query = select(Tag.nickname).where(Tag.user_id == user_id)
        result = await session.execute(query)
        return result.scalar() or "Anonymous"

    async def get_recomment_count(self, session: AsyncSession, parent_comment_id: int) -> int:
        parent_query = select(Comment.recomment_count).where(Comment.id == parent_comment_id)
        parent_result = await session.execute(parent_query)
        return parent_result.scalar() or 0
