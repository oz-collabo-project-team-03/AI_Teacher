import os
from typing import Optional

from dotenv import load_dotenv
from redis.asyncio import Redis

load_dotenv()

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_DB_CACHE = int(os.environ.get("REDIS_DB_CACHE", "0"))

redis_cache: Optional[Redis] = Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB_CACHE,
    decode_responses=True,
)


def get_redis_cache() -> Redis:
    return redis_cache
