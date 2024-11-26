from sqlalchemy import BigInteger, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from src.config.database import Base
from sqlalchemy.sql import func


class PostLike(Base):
    __tablename__ = "post_likes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    post_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("posts.id"), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, server_default=func.now())
