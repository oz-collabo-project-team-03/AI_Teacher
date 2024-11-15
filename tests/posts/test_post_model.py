import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from src.app.common.utils.consts import SocialProvider, UserRole, Visibility
from src.app.v1.post.enitity.post import Post
from src.app.v1.user.entity.user import User
from src.config.database.postgresql import Base, engine


class TestPostModel:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        self.session = async_session()

        yield

        await self.session.close()

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    @pytest.mark.asyncio
    async def test_create_post_with_valid_data(self):

        self.user_data = {
            "external_id": "1234",
            "email": "test@example.com",
            "phone": "01012345678",
            "password": "password",
            "profile_image": "http://example.com/image.png",
            "social_provider": SocialProvider.GOOGLE,
            "role": UserRole.student,
            "is_active": True,
        }

        user = User(**self.user_data)

        self.session.add(user)
        await self.session.commit()

        self.post_data = {
            "external_id": "test123456",
            "author_id": user.id,
            "content": "테스트 게시글입니다.",
            "visibility": Visibility.PUBLIC,
            "is_with_teacher": False,
        }

        post = Post(**self.post_data)

        self.session.add(post)
        await self.session.commit()

        result = await self.session.get(Post, post.id)

        assert result.external_id == self.post_data["external_id"]
        assert result.author_id == self.post_data["author_id"]
        assert result.content == self.post_data["content"]
        assert result.visibility == self.post_data["visibility"]
        assert result.is_with_teacher == self.post_data["is_with_teacher"]
        assert result.like_count == 0
        assert result.comment_count == 0
