import os
from datetime import datetime

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.app.common.utils.consts import SocialProvider, UserRole, Visibility
from src.app.v1.comment.entity.comment import Comment
from src.app.v1.post.entity.post import Post
from src.app.v1.user.entity.user import User
from src.config.database import Base

load_dotenv()

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


@pytest.fixture(scope="function")
def fake_db():
    engine = create_engine(TEST_DATABASE_URL, echo=True)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    yield session
    # 각 테스트 후 롤백 및 세션 종료
    session.rollback()
    session.close()
    # 테스트 완료 후 데이터베이스를 유지하고 싶다면 주석 처리
    Base.metadata.drop_all(bind=engine)


# 댓글 생성 테스트
def test_create_comment(fake_db):
    # 유저 생성
    user = User(
        id=1,
        external_id="user123",
        email="user@example.com",
        phone="01012345678",
        password="securepassword",
        profile_image="http://example.com/user.png",
        social_provider=SocialProvider.GOOGLE,
        role=UserRole.student,
        is_active=True,
    )
    fake_db.add(user)
    fake_db.commit()

    # 게시글 생성
    post = Post(
        id=1,
        external_id="post123",
        author_id=user.id,
        content="테스트 게시글입니다.",
        visibility=Visibility.PUBLIC,
        is_with_teacher=False,
    )
    fake_db.add(post)
    fake_db.commit()

    # 댓글 생성
    comment = Comment(
        id=1,
        post_id=post.id,
        author_id=user.id,
        content="테스트 댓글입니다.",
        recomment_count=0,
    )
    fake_db.add(comment)
    fake_db.commit()

    # 댓글 확인
    retrieved_comment = fake_db.query(Comment).filter_by(id=comment.id).first()
    assert retrieved_comment is not None
    assert retrieved_comment.content == "테스트 댓글입니다."
    assert retrieved_comment.recomment_count == 0
    assert isinstance(retrieved_comment.created_at, datetime)


# 게시글 삭제 시 댓글도 삭제되는지 확인
def test_comment_deletion_on_post_delete(fake_db):
    # 유저 생성
    user = User(
        id=2,
        external_id="user456",
        email="user2@example.com",
        password="securepassword",
        social_provider=SocialProvider.KAKAO,
        role=UserRole.teacher,
        is_active=True,
    )
    fake_db.add(user)
    fake_db.commit()

    # 게시글 생성
    post = Post(
        id=2,
        external_id="post456",
        author_id=user.id,
        content="삭제 테스트 게시글입니다.",
        visibility=Visibility.PUBLIC,
        is_with_teacher=False,
    )
    fake_db.add(post)
    fake_db.commit()

    # 댓글 생성
    comment = Comment(
        id=2,
        post_id=post.id,
        author_id=user.id,
        content="삭제 테스트 댓글입니다.",
        recomment_count=0,
    )
    fake_db.add(comment)
    fake_db.commit()

    # 게시글 삭제
    fake_db.delete(post)
    fake_db.commit()

    # 새로운 세션으로 댓글 조회
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=fake_db.bind)
    new_session = Session()

    # 댓글이 삭제되었는지 확인
    deleted_comment = new_session.query(Comment).filter_by(id=2).first()
    assert deleted_comment is None

    # 세션 닫기
    new_session.close()


# 댓글 생성 시 필수 필드만으로 정상 생성 확인
def test_comment_creation_with_minimum_fields(fake_db):
    # 유저 생성
    user = User(
        id=3,
        external_id="user789",
        email="user3@example.com",
        password="securepassword",
        social_provider=SocialProvider.GOOGLE,
        role=UserRole.student,
        is_active=True,
    )
    fake_db.add(user)
    fake_db.commit()

    # 게시글 생성
    post = Post(
        id=3,
        external_id="post789",
        author_id=user.id,
        content="최소 필드 테스트 게시글입니다.",
        visibility=Visibility.PUBLIC,
        is_with_teacher=False,
    )
    fake_db.add(post)
    fake_db.commit()

    # 댓글 생성
    comment = Comment(
        id=3,
        post_id=post.id,
        author_id=user.id,
        content="최소 필드 테스트 댓글입니다.",
    )
    fake_db.add(comment)
    fake_db.commit()

    # 댓글 확인
    retrieved_comment = fake_db.query(Comment).filter_by(id=comment.id).first()
    assert retrieved_comment is not None
    assert retrieved_comment.content == "최소 필드 테스트 댓글입니다."
    assert retrieved_comment.recomment_count == 0  # 기본값 확인
