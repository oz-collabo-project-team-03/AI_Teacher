from sqlalchemy import BigInteger, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from src.app.common.utils.consts import GradeNumber
from src.config.database import Base


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    school: Mapped[str] = mapped_column(String(20))
    grade: Mapped[GradeNumber] = mapped_column(Enum(GradeNumber))
    career_aspiration: Mapped[str] = mapped_column(String(30), nullable=True)
    interests: Mapped[str] = mapped_column(String(30), nullable=True)
    description: Mapped[str] = mapped_column(String(25), nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)

