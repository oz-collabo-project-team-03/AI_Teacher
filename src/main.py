import asyncio
import logging
import os
import sys
from pathlib import Path

# 프로젝트 루트 디렉토리를 sys.path에 추가
# 상단에 위치 필수 !
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from contextlib import asynccontextmanager

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.app.common.utils.websocket_manager import manager

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# 여기부터 router 추가
from src.app.router import (
    auth_router,
    chat_router,
    comment_router,
    post_router,
    user_router,
    websocket_router,
)

load_dotenv()

KAFKA_SERVER = os.environ.get("KAFKA_SERVER")
CHAT_TOPIC = os.environ.get("CHAT_TOPIC")
CONSUMER_GROUP = os.environ.get("CONSUMER_GROUP")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Kafka producer 초기화
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_SERVER,  # type: ignore
        # value_serializer=lambda x: json.dumps(x).encode("utf-8"),
        acks="all",
    )
    await producer.start()  # type: ignore

    # Kafka consumer 초기화
    consumer = AIOKafkaConsumer(
        CHAT_TOPIC,
        bootstrap_servers=KAFKA_SERVER,  # type: ignore
        # value_deserializer=lambda x: json.loads(x.decode("utf-8")),
        group_id=CONSUMER_GROUP,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        session_timeout_ms=30000,  # 세션 타임아웃 증가
        rebalance_timeout_ms=60000,  # 리밸런스 타임아웃 증가
        heartbeat_interval_ms=10000,  # 하트비트 주기 설정
    )
    await consumer.start()

    await manager.initialize(producer, consumer)

    # Kafka consumer 작업 시작
    asyncio.create_task(manager.consume_messages())
    yield

    # Ensure clean shutdown
    await manager.stop()
    await producer.stop()  # type: ignore
    await consumer.stop()  # type: ignore


main_router = APIRouter(prefix="/api/v1")


# 각 라우터를 메인 라우터에 포함
main_router.include_router(post_router)
main_router.include_router(auth_router)
main_router.include_router(chat_router)
main_router.include_router(comment_router)
main_router.include_router(user_router)
main_router.include_router(websocket_router)


app = FastAPI(debug=True, lifespan=lifespan)
app.include_router(main_router)


@app.middleware("http")
async def cors_debugging(request: Request, call_next):
    print(f"Request origin: {request.headers.get('origin')}")
    response = await call_next(request)
    print(f"Response CORS headers: {response.headers}")
    return response


origins = [
    "https://znrrz9fb6257.edge.naverncp.com",
    "https://sam.kprolabs.space",
    "http://front.suhaengssaem.bucket.s3-website.kr.object.ncloudstorage.com/",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_origin_regex="http://111\\.111\\.111\\.111(:\\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000)
