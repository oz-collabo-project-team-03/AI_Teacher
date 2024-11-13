import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from src.config.database import Base
from src.app.v1.user.entity.user import User
from src.app.common.utils.consts import UserRole, SocialProvider

@pytest.fixture(scope='function')
def fake_db():
    engine = create_engine("sqlite:///:memory:", echo=True)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    yield session
    # 각 테스트 후 롤백 및 세션 종료
    session.rollback()
    session.close()

#user 인스턴스 생성해서 세션에 추가한 후 커밋 후 생성된 유저가 데이터베이스 존재하는지 확인
def test_create_user(fake_db):
    try:
        user = User(
            id=1,
            external_id="1234",
            email="test@example.com",
            phone="01012345678",
            password="password",
            profile_image="http://example.com/image.png",
            social_provider=SocialProvider.GOOGLE,
            role=UserRole.student,
            is_active=True,
        )
        fake_db.add(user)
        fake_db.commit()

        retrieved_user = fake_db.query(User).filter_by(email="test@example.com").first()
        assert retrieved_user is not None
        assert retrieved_user.email == "test@example.com"
        assert retrieved_user.is_active is True
        assert retrieved_user.created_at is not None
        assert retrieved_user.updated_at is not None
    except IntegrityError:
        fake_db.rollback()
        raise

#email->unique 여서 같은 이메일 가진 두 user 인스턴스 생성시 IntegrityError 발생되는 지 확인
def test_unique_email(fake_db):
    try:
        user1 = User(
            id=2,
            external_id="12345",
            email="unique@example.com",
            password="password1",
            social_provider=SocialProvider.GOOGLE,
            role=UserRole.teacher,
        )
        fake_db.add(user1)
        fake_db.commit()

        user2 = User(
            id=3,
            external_id="12346",
            email="unique@example.com",
            password="password2",
            social_provider=SocialProvider.NAVER,
            role=UserRole.student,
        )
        fake_db.add(user2)
        with pytest.raises(IntegrityError):
            fake_db.commit()
    except IntegrityError:
        fake_db.rollback()
        raise

# default 값 설정해 놓은 최소 필수 필드 만으로 user 생성 되는 지 확인
def test_defaults(fake_db):
    try:
        user = User(
            id=4,
            external_id="12347",
            email="default@example.com",
            password="password",
            social_provider=SocialProvider.KAKAO,
            role=UserRole.teacher,
        )
        fake_db.add(user)
        fake_db.commit()

        retrieved_user = fake_db.query(User).filter_by(email="default@example.com").first()
        assert retrieved_user.is_active is True
        assert isinstance(retrieved_user.created_at, datetime)
        assert isinstance(retrieved_user.updated_at, datetime)
    except IntegrityError:
        fake_db.rollback()
        raise
