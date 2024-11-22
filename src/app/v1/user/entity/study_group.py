from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.config.database import Base


class StudyGroup(Base):
    __tablename__ = "study_groups"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("students.id"), nullable=False)
    teacher_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("teachers.id"), nullable=False)
