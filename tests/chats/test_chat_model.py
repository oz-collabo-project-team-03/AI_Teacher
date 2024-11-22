import os

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.future import select

from src.app.common.utils.consts import MessageType, SocialProvider, UserRole
from src.app.v1.chat.entity.participant import Participant
from src.app.v1.chat.entity.message import Message
from src.app.v1.chat.entity.room import Room
from src.app.v1.user.entity.user import User
from src.config.database import Base

load_dotenv()

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


# 비동기 세션 픽스처 생성
@pytest_asyncio.fixture(scope="function")
async def async_session():
    """비동기 데이터베이스 세션 생성"""
    if TEST_DATABASE_URL is None:
        raise ValueError("TEST_DATABASE_URL environment variable is not set")
    engine = create_async_engine(TEST_DATABASE_URL, echo=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with AsyncSessionLocal() as session:
        yield session
        await session.close()


@pytest.fixture
async def test_user(async_session):
    user = await async_session.execute(select(User).filter_by(email="test@example.com"))
    user = user.scalar_one_or_none()
    if user is None:
        user = User(
            external_id="test123",
            email="test@example.com",
            password="hashed_password",
            social_provider=SocialProvider.KAKAO,
            role=UserRole.STUDENT,
            is_active=True,
            is_privacy_accepted=True,
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_room_생성(async_session):
    """방 엔티티 생성 테스트"""
    room = Room(help_checked=False, last_message="테스트 메시지")
    async_session.add(room)
    await async_session.commit()
    await async_session.refresh(room)

    assert room.id is not None
    assert room.help_checked is False
    assert room.last_message == "테스트 메시지"


@pytest.mark.asyncio
async def test_메시지_생성(async_session, test_user):
    """메시지 엔티티 생성 테스트"""
    room = Room(last_message="테스트 방")
    async_session.add(room)
    await async_session.flush()

    message = Message(room_id=room.id, content="안녕하세요", type=MessageType.TEXT, user_id=test_user.id)
    async_session.add(message)
    await async_session.commit()
    await async_session.refresh(message)

    assert message.id is not None
    assert message.content == "안녕하세요"


@pytest.mark.asyncio
async def test_채팅_참여자_생성(async_session, test_user):
    """채팅 참여자 엔티티 생성 테스트"""
    room = Room(last_message="테스트 방")
    async_session.add(room)
    await async_session.flush()

    participant = Participant(user_id=test_user.id, room_id=room.id)
    async_session.add(participant)
    await async_session.commit()

    # 참여자가 성공적으로 생성되었는지 확인
    result = await async_session.execute(select(Participant).filter_by(user_id=test_user.id, room_id=room.id))
    created_participant = result.scalar_one_or_none()
    assert created_participant is not None


@pytest.mark.asyncio
async def test_방_메시지_관계(async_session, test_user):
    """방과 메시지 간 관계 테스트"""
    room = Room(last_message="테스트 방")
    async_session.add(room)
    await async_session.flush()

    message1 = Message(room_id=room.id, content="첫 번째 메시지", type=MessageType.TEXT, user_id=test_user.id)
    message2 = Message(room_id=room.id, content="두 번째 메시지", type=MessageType.TEXT, user_id=test_user.id)
    async_session.add_all([message1, message2])
    await async_session.commit()

    result = await async_session.execute(select(Message).filter_by(room_id=room.id))
    room_messages = result.scalars().all()

    assert len(room_messages) == 2
    assert room_messages[0].content == "첫 번째 메시지"
    assert room_messages[1].content == "두 번째 메시지"
