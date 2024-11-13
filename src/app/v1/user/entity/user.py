from datetime import datetime

from sqlalchemy import Integer, String, BigInteger, DateTime, Boolean, Enum, func
from sqlalchemy.orm import Mapped, mapped_column
from src.config.database import Base
from src.app.common.utils.consts import UserRole, SocialProvider

class User(Base):
    __tablename__ = "users"

    id : Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    external_id : Mapped[str] = mapped_column(String(16), autoincrement=False)
    email : Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    phone : Mapped[str] = mapped_column(String(13), nullable=True)
    password : Mapped[str] = mapped_column(String(64))
    profile_image : Mapped[str] = mapped_column(String(255), nullable=True)
    social_provider : Mapped[SocialProvider] = mapped_column(Enum(SocialProvider))
    role : Mapped[UserRole] = mapped_column(Enum(UserRole))
    is_active : Mapped[bool] = mapped_column(Boolean, default=True)
    created_at : Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at : Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=datetime.now)
