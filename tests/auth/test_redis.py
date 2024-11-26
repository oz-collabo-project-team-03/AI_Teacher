import asyncio
import logging

from redis.asyncio import Redis

from src.app.common.utils.redis_utils import (
    delete_from_redis,
    get_from_redis,
    save_to_redis,
)
from src.config.database.redis import get_redis_cache

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def test_redis_connection():
    redis = Redis(host="localhost", port=6379, decode_responses=True)
    try:
        await redis.ping()
        print("Redis 연결 성공")
    except Exception as e:
        print(f"Redis 연결 실패: {e}")


asyncio.run(test_redis_connection())


async def test_redis_operations():
    key = "test_key"
    value = "test_value"
    expiry = 10  # 10초

    try:
        await save_to_redis(key, value, expiry)
        print(f"Redis에 데이터 저장 성공: {key} -> {value}")
    except Exception as e:
        print(f"Redis 데이터 저장 실패: {e}")
        return

    try:
        retrieved_value = await get_from_redis(key)
        print(f"Redis에서 조회된 데이터: {key} -> {retrieved_value}")
        assert retrieved_value == value, "저장된 값과 조회된 값이 다릅니다!"
    except Exception as e:
        print(f"Redis 데이터 조회 실패: {e}")
        return

    try:
        await delete_from_redis(key)
        print(f"Redis 데이터 삭제 성공: {key}")
    except Exception as e:
        print(f"Redis 데이터 삭제 실패: {e}")


asyncio.run(test_redis_operations())


async def test_verification_code_storage():
    redis = Redis(host="localhost", port=6379, decode_responses=True)
    email = "test@example.com"
    verification_code = "123456"
    redis_key = f"verification:email:{email}"
    expiry = 180

    try:
        await redis.delete(redis_key)  # 테스트 전에 키 삭제
        # Redis 저장
        await redis.set(redis_key, verification_code, ex=expiry)
        logger.info(f"Redis 저장 성공: Key={redis_key}, Value={verification_code}, Expiry={expiry}")

        # 데이터 확인
        stored_value = await redis.get(redis_key)
        ttl = await redis.ttl(redis_key)
        logger.info(f"저장된 값: {stored_value}, TTL: {ttl}초")
        assert stored_value == verification_code, "저장된 값이 인증 코드와 다릅니다."
        assert ttl > 0, "TTL이 유효하지 않습니다."

    except Exception as e:
        logger.error(f"Redis 테스트 실패: {e}")
        raise
