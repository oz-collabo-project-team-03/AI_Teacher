import os
from dotenv import load_dotenv
from redis.asyncio import Redis


load_dotenv()

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_DB_CACHE = int(os.environ.get("REDIS_DB_CACHE", "0"))

redis_cache: Redis = Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB_CACHE,
    decode_responses=True,
)

room_redis = Redis.from_url(f"redis://{REDIS_HOST}:{REDIS_PORT}", decode_responses=True)
# Pub/Sub 채널 이름 정의
ROOM_HELP_CHECKED_CHANNEL = "room:help_checked"


def get_redis_cache() -> Redis:
    return redis_cache
