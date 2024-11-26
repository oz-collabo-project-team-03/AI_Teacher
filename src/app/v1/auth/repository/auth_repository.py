# import ulid
# from sqlalchemy import select
# from sqlalchemy.ext.asyncio import AsyncSession
#
# from src.app.common.utils.consts import SocialProvider
# from src.app.v1.user.entity.organization import Organization
# from src.app.v1.user.entity.student import Student
# from src.app.v1.user.entity.teacher import Teacher
# from src.app.v1.user.entity.user import User
#
#
# class AuthRepository:
#     # 소셜 로그인 유저 조회
#     async def get_user_by_external_id(self, session: AsyncSession, external_id: str, provider: SocialProvider) -> User | None:
#
#         query = select(User).where(User.external_id == external_id).where(User.social_provider == provider)
#         result = await session.execute(query)
#         return result.scalars().first()
#
#     # 소셜 로그인 유저 생성
#     async def create_social_user(self, session: AsyncSession, provider: SocialProvider, user_data: dict) -> User:
#
#         async with session.begin():
#             external_id = ulid.new().str
#
#             user = User(
#                 external_id=external_id,
#                 social_provider=provider,
#                 nickname=user_data.get("nickname"),
#                 role=None,  # 초기에는 설정하지 않음
#             )
#             session.add(user)
#         return user
#
#     async def create_student(self, session: AsyncSession, user_data: dict):
#         async with session.begin():
#             user = await self.get_user_by_external_id(session, external_id=user_data["external_id"], provider=SocialProvider.KAKAO)
#             if not user:
#                 raise ValueError("사용자를 찾을 수 없습니다.")
#
#             student = Student(
#                 user_id=user.id,
#                 school=user_data["student_data"]["school"],
#                 grade=user_data["student_data"]["grade"],
#                 career_aspiration=user_data["student_data"].get("career_aspiration"),
#                 interest=user_data["student_data"].get("interest"),
#             )
#             session.add(student)
#
#     # 교사의 경우
#
#
# async def create_teacher(self, session: AsyncSession, user_data: dict):
#     async with session.begin():
#         user = await self.get_user_by_external_id(session, external_id=user_data["external_id"], provider=SocialProvider.KAKAO)
#         if not user:
#             raise ValueError("사용자를 찾을 수 없습니다.")
#
#         teacher = Teacher(user_id=user.id)
#         session.add(teacher)
#
#         organization = Organization(
#             name=user_data["teacher_data"]["organization_name"],
#             type=user_data["teacher_data"]["organization_type"],
#             position=user_data["teacher_data"]["position"],
#             teacher_id=teacher.id,
#         )
#         session.add(organization)
