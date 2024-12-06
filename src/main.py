import asyncio
import logging
import os
import json
import sys
import asyncio
import logging
from pathlib import Path

# 프로젝트 루트 디렉토리를 sys.path에 추가
# 상단에 위치 필수 !
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from src.app.common.utils.websocket_manager import manager
from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


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
        # value_serializer=lambda x: json.dumps(x).encode("utf-8"),
    )
    await producer.start()  # type: ignore

    # Kafka consumer 초기화
    consumer = AIOKafkaConsumer(
        CHAT_TOPIC,
        bootstrap_servers=KAFKA_SERVER,  # type: ignore
        # value_deserializer=lambda x: json.loads(x.decode("utf-8")),
        group_id=CONSUMER_GROUP,
        auto_offset_reset="latest",
        enable_auto_commit=True,
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


health_router = APIRouter(prefix="/api/v1", tags=["Health"])


@health_router.get("/health")
async def health_check():
    return {"status": "ok"}


app = FastAPI(debug=True, lifespan=lifespan)

app.include_router(post_router)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(comment_router)
app.include_router(user_router)
app.include_router(websocket_router)
app.include_router(health_router)


@app.middleware("http")
async def cors_debugging(request: Request, call_next):
    print(f"Request origin: {request.headers.get('origin')}")
    response = await call_next(request)
    print(f"Response CORS headers: {response.headers}")
    return response


origins = [
    "http://localhost:5173/",
    "http://localhost:5173",
    "https://localhost:5173/",
    "https://localhost:5173",
    "http://localhost:8000/",
    "http://localhost:8000",
    "http://sam-test.kprolabs.space:8000/",
    "http://sam-test.kprolabs.space:8000",
    "http://kong.kprolabs.space:8000/",
    "http://kong.kprolabs.space:8000",
    "http://158.180.84.161:8000/",
    "http://158.180.84.161:8000",
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
    # asyncio.run(main())
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
