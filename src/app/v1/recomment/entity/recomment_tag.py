from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.config.database import Base


class RecommentTag(Base):
    __tablename__ = "recomment_tags"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, nullable=False)
    recomment_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("recomments.id", ondelete="CASCADE"), nullable=False)
    tag_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tags.id", ondelete="CASCADE"), nullable=False)
