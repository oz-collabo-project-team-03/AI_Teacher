from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, validates
from sqlalchemy.sql import func

from src.app.common.utils.consts import Visibility
from src.config.database import Base


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, nullable=False)
    external_id: Mapped[str] = mapped_column(String(16), nullable=False)
    author_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    visibility: Mapped[str] = mapped_column(Enum(Visibility), default=Visibility.PUBLIC, nullable=False)
    like_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comment_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_with_teacher: Mapped[bool] = mapped_column(Boolean, nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("like_count >= 0", name="check_positive_like_count"),
        CheckConstraint("comment_count >= 0", name="check_positive_comment_count"),
    )

    # @validates("like_count", "comment_count") # 파이썬 코드 레벨에서 유효성 검사
    # def validate_positive_count(self, key, value):
    #     if value < 0:
    #         raise ValueError(f"{key} must be positive")
    #     return value
