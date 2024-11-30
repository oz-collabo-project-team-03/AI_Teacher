from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.app.v1.user.entity.teacher import Teacher
from src.app.v1.user.entity.student import Student
from src.app.v1.user.entity.study_group import StudyGroup


async def group_students_with_teachers(session: AsyncSession):
    """교사와 학생 데이터를 데이터베이스에서 가져와 그룹핑"""
    try:
        # 데이터베이스에서 교사와 학생 가져오기
        teacher_query = await session.execute(select(Teacher))
        teachers = teacher_query.scalars().all()

        student_query = await session.execute(select(Student))
        students = student_query.scalars().all()

        if not teachers:
            print("교사 데이터가 없습니다. 먼저 교사를 생성하세요.")
            return

        if not students:
            print("학생 데이터가 없습니다. 먼저 학생을 생성하세요.")
            return

        # 그룹핑 작업
        teacher_index = 0
        for i, student in enumerate(students):
            if i % 10 == 0 and i > 0:
                teacher_index += 1  # 다음 교사로 넘어감

            if teacher_index >= len(teachers):
                print("교사 수가 부족합니다. 더 많은 교사를 추가하세요.")
                break

            # StudyGroup 객체 생성
            study_group = StudyGroup(
                student_id=student.id,
                teacher_id=teachers[teacher_index].id
            )
            session.add(study_group)

        # 변경 사항 커밋
        await session.commit()
        print(f"학생과 교사 그룹핑이 완료되었습니다. 총 {len(students)}명의 학생이 그룹핑되었습니다.")
    except Exception as e:
        print(f"그룹핑 중 오류 발생: {e}")
        await session.rollback()
        raise
