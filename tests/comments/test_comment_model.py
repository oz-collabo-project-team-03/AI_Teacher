# from datetime import datetime
#
# import pytest
# import pytest_asyncio
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.orm import sessionmaker
#
# from src.app.common.utils.consts import SocialProvider, UserRole, Visibility
# from src.app.v1.comment.enitity.comment import Comment
# from src.app.v1.post.enitity.post import Post
# from src.app.v1.user.entity.user import User
# from src.config.database.postgresql import Base, engine
#
#
# class TestCommentModel:
#
#     @pytest_asyncio.fixture(scope="function", autouse=True)
#     async def setup(self):
#         # 테이블 생성
#         async with engine.begin() as conn:
#             await conn.run_sync(Base.metadata.create_all)
#
#         # 세션 생성
#         async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
#         self.session = async_session()
#
#         yield  # 테스트 실행
#
#         # 세션 닫기
#         await self.session.close()
#
#         # 테이블 삭제
#         async with engine.begin() as conn:
#             await conn.run_sync(Base.metadata.drop_all)
#
#     async def create_user(self, external_id, email, role):
#         """유저 생성 헬퍼 함수"""
#         user = User(
#             external_id=external_id,
#             email=email,
#             phone="01012345678",
#             password="securepassword",
#             profile_image="http://example.com/user.png",
#             social_provider=SocialProvider.GOOGLE,
#             role=role,
#             is_active=True,
#         )
#         self.session.add(user)
#         await self.session.commit()
#         await self.session.refresh(user)  # 세션 동기화
#         return user
#
#     async def create_post(self, author_id, external_id, content):
#         """게시글 생성 헬퍼 함수"""
#         post = Post(
#             external_id=external_id,
#             author_id=author_id,
#             content=content,
#             visibility=Visibility.PUBLIC,
#             is_with_teacher=False,
#         )
#         self.session.add(post)
#         await self.session.commit()
#         await self.session.refresh(post)  # 세션 동기화
#         return post
#
#     @pytest.mark.asyncio
#     async def test_create_comment(self):
#         user = await self.create_user("user123", "user@example.com", UserRole.student)
#         post = await self.create_post(user.id, "post123", "테스트 게시글입니다.")
#
#         # 댓글 생성
#         comment = Comment(
#             post_id=post.id,
#             author_id=user.id,
#             content="테스트 댓글입니다.",
#             recomment_count=0,
#         )
#         self.session.add(comment)
#         await self.session.commit()
#         await self.session.refresh(comment)
#
#         # 댓글 확인
#         result = await self.session.get(Comment, comment.id)
#         assert result is not None
#         assert result.content == "테스트 댓글입니다."
#         assert result.recomment_count == 0
#         assert isinstance(result.created_at, datetime)
