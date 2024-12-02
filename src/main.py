import asyncio
import logging
import os
import platform
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.DEBUG)

# 프로젝트 루트 디렉토리를 sys.path에 추가
# 상단에 위치 필수 !
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# 여기부터 router 추가
from src.app.router import (
    auth_router,
    chat_router,
    comment_router,
    post_router,
    user_router,
)

app = FastAPI(debug=True)

app.include_router(post_router)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(comment_router)
app.include_router(user_router)

origins = ["http://localhost:5173", "https://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_origin_regex="http://111\\.111\\.111\\.111(:\\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)

api_router = APIRouter(prefix="/api/v1")


def run_check_script():
    system = platform.system().lower()

    if system == "darwin":  # Mac OS
        script_path = "./scripts/check.sh"
    elif system == "linux":
        script_path = "./scripts/check.sh"
    elif system == "windows":
        script_path = os.path.join(project_root, "scripts", "check.bat")
    else:
        print(f"Unsupported operating system: {system}")
        return

    try:
        print(f"Running {script_path}...")
        result = subprocess.run([script_path], capture_output=True, text=True, shell=True)
        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr, file=sys.stderr)
    except FileNotFoundError:
        print(f"Error: {script_path} not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

# 임시 데이터 생성 -> 학생 5명, 선생님 50명, 그룹 10명씩
# from sqlalchemy.ext.asyncio import AsyncEngine
# from src.config.database.postgresql import Base, SessionLocal, engine
# 학생 생성, 선생님 생성, 그룹 생성 임포트
# from generate_data.teacher import insert_teachers_async
# from generate_data.student import insert_students_async
# from generate_data.studygroup import group_students_with_teachers

# async def initialize_database(async_engine: AsyncEngine):
#
#     async with async_engine.begin() as conn:
#
#         await conn.run_sync(Base.metadata.create_all)  # 새 테이블 생성
#
# async def main():
#     # 데이터베이스 초기화
#     print("데이터베이스 초기화 중...")
#     await initialize_database(engine)
#
#     # 데이터 삽입
#     print("초기 데이터를 생성합니다...")
#     async with SessionLocal() as session:
        # await insert_teachers_async(session, num_teachers=5)
        # await insert_students_async(session, num_students=50)
        # await group_students_with_teachers(session)

if __name__ == "__main__":
    # run_check_script()
    # asyncio.run(main())
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)