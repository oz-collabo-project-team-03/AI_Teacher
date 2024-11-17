from sqlalchemy import BigInteger, String, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from src.config.database import Base


class PostImage(Base):
    __tablename__ = "post_images"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, nullable=False)
    image_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("images.id"), nullable=False)
    post_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("posts.id"), nullable=False)
