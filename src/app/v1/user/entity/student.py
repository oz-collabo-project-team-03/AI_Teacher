from sqlalchemy import BigInteger, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.common.utils.consts import GradeNumber
from src.config.database import Base


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    school: Mapped[str] = mapped_column(String(20))
    grade: Mapped[GradeNumber] = mapped_column(Enum(GradeNumber, name="grade_number_enum"), nullable=False)
    career_aspiration: Mapped[str] = mapped_column(String(30), nullable=True)
    interest: Mapped[str] = mapped_column(String(30), nullable=True)
    description: Mapped[str] = mapped_column(String(25), nullable=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)

    user = relationship("User", back_populates="student")
