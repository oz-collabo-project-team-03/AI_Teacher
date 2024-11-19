from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.config.database import Base


class ChatParticipant(Base):
    __tablename__ = "chat_participants"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user.id"), nullable=False)
    room_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("room.id"), nullable=False)
