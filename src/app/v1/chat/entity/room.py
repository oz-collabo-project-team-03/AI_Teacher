from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, func, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.config.database import Base


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, nullable=False)
    title: Mapped[str] = mapped_column(String(30), nullable=True, default="Empty")
    help_checked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    participant = relationship("Participant", back_populates="room")
