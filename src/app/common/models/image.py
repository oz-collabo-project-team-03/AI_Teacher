from sqlalchemy import BigInteger, String, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from src.config.database import Base


class Image(Base):
    __tablename__ = "images"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, nullable=False)
    image_path: Mapped[str] = mapped_column(String(255), nullable=False)
