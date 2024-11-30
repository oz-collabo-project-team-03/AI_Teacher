# from src.app.common.utils.timezone import get_kst_now
from datetime import datetime

from bson import ObjectId
from odmantic import Field, Model


# MongoDB Collection
class Message(Model):
    id: ObjectId = Field(default_factory=ObjectId, primary_field=True)
    room_id: int
    title: str
    sender_id: int
    message_type: str
    room_id: int  # type: ignore
    content: str
    # FIXME: 현재 시간 적용
    timestamp: datetime

    model_config = {  # type: ignore
        "collection": "chat",
    }


# 이전 RDBMS Table

# from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, String, func
# from sqlalchemy.orm import Mapped, mapped_column, relationship

# from src.app.common.utils.consts import MessageType
# from src.config.database import Base


# class Message(Base):
#     __tablename__ = "messages"
#
#     id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, nullable=False)
#     participant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("participants.id"), nullable=False)
#     user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
#     room_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
#     content: Mapped[str] = mapped_column(String(300), nullable=False)
#     message_type: Mapped[MessageType] = mapped_column(Enum(MessageType), nullable=False, default=MessageType.TEXT)
#     created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
#     updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
#     participants = relationship("Participant")
