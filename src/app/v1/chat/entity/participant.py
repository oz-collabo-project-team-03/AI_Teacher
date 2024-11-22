from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.config.database import Base


class Participant(Base):
    __tablename__ = "participants"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    room_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("rooms.id"), nullable=False)
    user = relationship("User", back_populates="participant")
    room = relationship("Room", back_populates="participant")
    message = relationship("Message", back_populates="participant")
