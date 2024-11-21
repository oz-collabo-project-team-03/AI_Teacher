from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func, Enum
from sqlalchemy.orm import Mapped, mapped_column

from src.config.database import Base
from src.app.common.utils.consts import MessageType


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, nullable=False)
    room_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    content: Mapped[str] = mapped_column(String(300), nullable=False)
    type: Mapped[MessageType] = mapped_column(Enum(MessageType), nullable=False, default=MessageType.TEXT)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
