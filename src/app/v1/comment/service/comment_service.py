from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.v1.comment.entity.comment import Comment
from src.app.v1.comment.repository.comment_repo import CommentRepository
from src.app.v1.comment.schema.requestDto import CommentCreateRequest
from src.app.v1.comment.schema.responseDto import CommentCreateResponse, CommentResponse
from src.app.v1.post.entity.post import Post


class CommentService:
    def __init__(self):
        self.comment_repository = CommentRepository()

    async def get_post_id_from_external_id(self, session: AsyncSession, external_id: str) -> int:
        """external_id를 실제 post_id로 변환"""
        post_id = await self.comment_repository.get_post_id_from_external_id(session, external_id)
        if not post_id:
            raise ValueError("해당 external_id에 해당하는 게시글이 없습니다.")
        return post_id

    async def create_comment_with_tags(
        self, session: AsyncSession, post_id: int, author_id: int, payload: CommentCreateRequest
    ) -> CommentCreateResponse:
        """댓글 생성"""
        # 부모 댓글 유효성 검사
        parent_comment = None
        if payload.parent_comment_id:
            parent_comment = await self.comment_repository.get_comment(session, payload.parent_comment_id)
            if not parent_comment:
                raise ValueError("대댓글 대상 댓글을 찾을 수 없습니다.")
            if parent_comment.post_id != post_id:
                raise ValueError("댓글은 동일한 게시글에만 대댓글로 작성할 수 있습니다.")
            parent_comment.recomment_count += 1
            session.add(parent_comment)

        # 댓글 생성
        comment = Comment(
            post_id=post_id,
            author_id=author_id,
            content=payload.content,
            parent_comment_id=payload.parent_comment_id,
        )

        # 태그 유효성 검사 및 추가
        tags = await self.comment_repository.get_valid_tags(session, payload.tags or [])
        invalid_tags = set(payload.tags or []) - {tag.nickname for tag in tags}
        if invalid_tags:
            raise ValueError(f"유효하지 않은 태그입니다: {', '.join(invalid_tags)}")

        await self.comment_repository.create_comment(session, comment, tags)

        # 댓글 생성 후 comment_count 증가
        is_parent = payload.parent_comment_id is None  # 대댓글이 아니면 True
        await self.comment_repository.increment_comment_count(session, post_id, is_parent)

        # 닉네임 및 프로필 이미지 조회
        user_info = await self.comment_repository.get_user_info(session, author_id)

        # `post_id`를 `external_id`로 변환
        post_external_id_query = select(Post.external_id).where(Post.id == comment.post_id)
        post_external_id_result = await session.execute(post_external_id_query)
        post_external_id = post_external_id_result.scalar_one()

        await session.commit()

        # 응답 생성
        return CommentCreateResponse(
            comment_id=comment.id,
            post_id=post_external_id,
            user_id=user_info["id"],
            author_nickname=user_info["nickname"],
            content=comment.content,
            created_at=comment.created_at,
            tags=payload.tags or [],
            parent_comment_id=payload.parent_comment_id,
            recomment_count=parent_comment.recomment_count if parent_comment else 0,
        )

    async def get_comments_with_tags(self, session: AsyncSession, post_id: int):
        """댓글 조회"""
        comments_with_tags = await self.comment_repository.get_comments_by_post_id(session, post_id)

        author_ids = {row.Comment.author_id for row in comments_with_tags}
        user_info_map = {
            author_id: await self.comment_repository.get_user_info(session, author_id)
            for author_id in author_ids
        }

        parent_comments = [row for row in comments_with_tags if row.Comment.parent_comment_id is None]
        child_comments = [row for row in comments_with_tags if row.Comment.parent_comment_id is not None]

        parent_map = {row.Comment.id: row for row in parent_comments}
        for child_row in child_comments:
            parent_row = parent_map.get(child_row.Comment.parent_comment_id)
            if parent_row:
                if not hasattr(parent_row.Comment, "children"):
                    parent_row.Comment.children = []
                parent_row.Comment.children.append(child_row)

        return [
            self._convert_to_response(
                row.Comment,
                row.tags or [],
                row.post_external_id,  # Post의 external_id를 응답에 포함
                user_info_map[row.Comment.author_id]["id"],  # User의 실제 id 전달
                user_info_map[row.Comment.author_id]["nickname"],  # Tag 모델의 nickname 반환
                user_info_map[row.Comment.author_id]["profile_image"],
            )
            for row in parent_comments
        ]

    def _convert_to_response(
        self,
        comment: Comment,
        tags: list[str],
        post_external_id: str,
        user_id: str,
        author_nickname: str,
        profile_image: str | None,
    ) -> CommentResponse:
        """댓글 데이터 변환"""
        return CommentResponse(
            comment_id=comment.id,
            post_id=post_external_id,  # post_external_id를 사용
            user_id=user_id,
            author_nickname=author_nickname,
            profile_image=profile_image,
            content=comment.content,
            created_at=comment.created_at,
            tags=[tag for tag in tags if tag is not None],
            parent_comment_id=comment.parent_comment_id,
            recomment_count=comment.recomment_count,
            children=[
                self._convert_to_response(
                    child.Comment,
                    child.tags or [],
                    post_external_id,  # 동일한 post_external_id를 자식에도 사용
                    user_id,
                    author_nickname,
                    profile_image,
                )
                for child in getattr(comment, "children", [])
            ],
        )

    async def delete_comment(self, session: AsyncSession, comment_id: int, user_id: int):
        """댓글 삭제"""
        async with session.begin():
            comment = await self.comment_repository.get_comment(session, comment_id)
            if not comment:
                raise ValueError("댓글을 찾을 수 없습니다.")
            if comment.author_id != user_id:
                raise ValueError("해당 댓글의 작성자가 아닙니다.")
            if comment.parent_comment_id:
                parent_comment = await self.comment_repository.get_comment(session, comment.parent_comment_id)
                if parent_comment:
                    parent_comment.recomment_count -= 1
                    session.add(parent_comment)

            # 댓글 삭제
            await self.comment_repository.delete_comment(session, comment)

            # 댓글 삭제 후 comment_count 감소
            is_parent = comment.parent_comment_id is None  # 대댓글이 아니면 True
            await self.comment_repository.decrement_comment_count(session, comment.post_id, is_parent)
