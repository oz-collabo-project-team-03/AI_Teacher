from sqlalchemy.ext.asyncio import AsyncSession

from src.app.v1.comment.entity.comment import Comment
from src.app.v1.comment.repository.comment_repo import CommentRepository
from src.app.v1.comment.schema.requestDto import CommentCreateRequest
from src.app.v1.comment.schema.responseDto import CommentCreateResponse, CommentResponse


class CommentService:
    def __init__(self):
        self.comment_repository = CommentRepository()

    async def create_comment_with_tags(
        self, session: AsyncSession, post_id: int, author_id: int, payload: CommentCreateRequest
    ) -> CommentCreateResponse:
        async with session.begin():
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

            # 닉네임 조회
            author_nickname = await self.comment_repository.get_user_nickname(session, author_id)

        return CommentCreateResponse(
            comment_id=comment.id,
            post_id=comment.post_id,
            author_id=comment.author_id,
            author_nickname=author_nickname,
            content=comment.content,
            created_at=comment.created_at,
            tags=payload.tags or [],
            parent_comment_id=payload.parent_comment_id,
            recomment_count=parent_comment.recomment_count if parent_comment else 0,
        )

    async def get_comments_with_tags(self, session: AsyncSession, post_id: int):
        # 댓글 및 태그 데이터 조회
        comments_with_tags = await self.comment_repository.get_comments_by_post_id(session, post_id)

        # 닉네임 매핑
        author_ids = {row.Comment.author_id for row in comments_with_tags}
        nickname_map = {author_id: await self.comment_repository.get_user_nickname(session, author_id) for author_id in author_ids}

        # 부모 댓글과 대댓글 분리
        parent_comments = [row for row in comments_with_tags if row.Comment.parent_comment_id is None]
        child_comments = [row for row in comments_with_tags if row.Comment.parent_comment_id is not None]

        # 부모 댓글 ID 맵핑
        parent_map = {row.Comment.id: row for row in parent_comments}
        for child_row in child_comments:
            parent_row = parent_map.get(child_row.Comment.parent_comment_id)
            if parent_row:
                if not hasattr(parent_row.Comment, "children"):
                    parent_row.Comment.children = []
                parent_row.Comment.children.append(child_row)

        # Pydantic 모델로 변환
        return [self._convert_to_response(row.Comment, row.tags or [], nickname_map) for row in parent_comments]

    def _convert_to_response(self, comment: Comment, tags: list[str], nickname_map: dict[int, str]) -> CommentResponse:
        return CommentResponse(
            comment_id=comment.id,
            post_id=comment.post_id,
            author_id=comment.author_id,
            author_nickname=nickname_map.get(comment.author_id, "Anonymous"),
            content=comment.content,
            created_at=comment.created_at,
            tags=[tag for tag in tags if tag is not None],
            parent_comment_id=comment.parent_comment_id,
            recomment_count=comment.recomment_count,
            children=[self._convert_to_response(child.Comment, child.tags or [], nickname_map) for child in getattr(comment, "children", [])],
        )

    async def delete_comment(self, session: AsyncSession, comment_id: int, user_id: int):
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
            await self.comment_repository.delete_comment(session, comment)
