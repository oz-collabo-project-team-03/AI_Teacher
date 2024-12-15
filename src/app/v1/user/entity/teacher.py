from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.config.database import Base


class Teacher(Base):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)

    # ono-to-one 관계
    user = relationship("User", back_populates="teacher", uselist=False)
    organization = relationship("Organization", back_populates="teacher", uselist=False, cascade="all, delete-orphan")
