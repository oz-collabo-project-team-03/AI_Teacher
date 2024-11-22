import os

import redis.asyncio as redis
from fastapi import HTTPException

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)


async def test_redis_connection():
    try:
        pong = await redis_client.ping()
        print(f"Redis 연결 성공: {pong}")
    except Exception as e:
        print(f"Redis 연결 실패: {e}")


async def save_to_redis(key: str, value: str, expiry: int):
    try:
        await redis_client.set(key, value, ex=expiry)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis 저장 오류: {str(e)}")


async def get_from_redis(key: str) -> str | None:
    try:
        return await redis_client.get(key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis 조회 오류: {str(e)}")


async def delete_from_redis(key: str):
    try:
        await redis_client.delete(key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis 삭제 오류: {str(e)}")


def get_redis_key_jti(jti: str) -> str:
    return f"jti:{jti}"


def get_redis_key_refresh_token(user_id: int) -> str:
    return f"refresh_token:{user_id}"


async def add_to_blacklist(token: str, expiry: int):
    await save_to_redis(f"blacklist:{token}", "blacklisted", expiry)


async def is_blacklisted(token: str) -> bool:
    return await get_from_redis(f"blacklist:{token}") is not None


async def is_jti_used(jti: str) -> bool:
    return await get_from_redis(f"jti:{jti}") is not None


async def mark_jti_used(jti: str, expiry: int):
    await save_to_redis(f"jti:{jti}", "used", expiry)


# 여기부터 로직 확인

# #소셜 로그인
# REFRESH_TOKEN_TTL = timedelta(days=7)
#
#
# # Redis에 자체 리프레시 토큰 저장
# async def save_social_refresh_token(id: int, jti: str) -> None:
#     key = f"refresh_token:{id}"
#     token_data = {"jti": jti}
#
#     try:
#         await redis_client.setex(key, REFRESH_TOKEN_TTL, json.dumps(token_data))
#     except RedisError as e:
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Redis 서버 오류입니다.") from e
#
#
# async def verify_refresh_token(id: int, jti: str) -> bool:
#     key = f"refresh_token:{id}"
#
#     try:
#         stored_token_data = await redis_client.get(key)
#         if not stored_token_data:
#             return False
#
#         token_data = json.loads(stored_token_data)
#         return token_data.get("jti") == jti
#     except RedisError as e:
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Redis 서버 오류입니다.") from e
#
#
# async def delete_user_token(id: int) -> None:
#     key = f"refresh_token:{id}"
#     try:
#         await redis_client.delete(key)
#     except RedisError as e:
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Redis 서버 오류입니다.") from e
