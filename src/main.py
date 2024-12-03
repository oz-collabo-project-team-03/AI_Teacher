import asyncio
import logging
import os
import json
import platform
import subprocess
import sys
import asyncio
from pathlib import Path

# 프로젝트 루트 디렉토리를 sys.path에 추가
# 상단에 위치 필수 !
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from src.app.common.utils.websocket_manager import manager
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.DEBUG)


# 여기부터 router 추가
from src.app.router import auth_router, chat_router, comment_router, post_router, user_router, websocket_router

load_dotenv()

KAFKA_SERVER = os.environ.get("KAFKA_SERVER")
CHAT_TOPIC = os.environ.get("CHAT_TOPIC")
CONSUMER_GROUP = os.environ.get("CONSUMER_GROUP")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Kafka producer 초기화
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_SERVER,  # type: ignore
        value_serializer=lambda x: json.dumps(x).encode("utf-8"),
    )
    await producer.start()  # type: ignore

    await manager.initialize(producer)

    # Kafka consumer 초기화
    consumer = AIOKafkaConsumer(
        CHAT_TOPIC,
        bootstrap_servers=KAFKA_SERVER,  # type: ignore
        value_deserializer=lambda x: json.loads(x.decode("utf-8")),
        group_id=CONSUMER_GROUP,
        auto_offset_reset="latest",
    )
    await consumer.start()

    # FastAPI state에 저장
    app.state.kafka_producer = producer
    app.state.kafka_consumer = consumer

    # Kafka consumer 작업 시작
    asyncio.create_task(consume_messages(app))

    yield

    # 종료 시 Kafka 연결 종료
    await producer.stop()  # type: ignore
    await consumer.stop()  # type: ignore


async def consume_messages(app: FastAPI):
    """Kafka consumer message 처리"""
    try:
        async for message in app.state.kafka_consumer:
            await manager.broadcast_message(message.value)
    except Exception as e:
        print(f"Error consuming kafka messages: {e}")


app = FastAPI(debug=True, lifespan=lifespan)

app.include_router(post_router)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(comment_router)
app.include_router(user_router)
app.include_router(websocket_router)

origins = [
    "http://localhost:5173",
    "https://localhost:5173",
    "http://localhost:8000",
    "http://sam-test.kprolabs.space:8000",
    "http://kong.kprolabs.space:8000",
    "158.180.84.161:8000",
]

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

#     async with async_engine.begin() as conn:

#         await conn.run_sync(Base.metadata.create_all)  # 새 테이블 생성


# async def main():
#     # 데이터베이스 초기화
#     print("데이터베이스 초기화 중...")
#     await initialize_database(engine)

#     # 데이터 삽입
#     print("초기 데이터를 생성합니다...")
#     async with SessionLocal() as session:
#         # await insert_teachers_async(session, num_teachers=5)
#         # await insert_students_async(session, num_students=50)
#         # await group_students_with_teachers(session)


if __name__ == "__main__":
    # run_check_script()
    # asyncio.run(main())
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
