import logging

from fastapi import HTTPException

from src.config.database.redis import get_redis_cache

redis_client = get_redis_cache()

# TTL 설정
REFRESH_TOKEN_TTL = 7 * 24 * 3600  # 7일
JTI_TTL = 15 * 60  # 15분

# 로거 설정
logger = logging.getLogger(__name__)


# Redis 작업 함수
async def save_to_redis(key: str, value: str, expiry: int):
    try:
        await redis_client.set(key, value, ex=expiry)
    except Exception as e:
        logger.error(f"Redis 저장 오류 (Key: {key}): {e}")
        raise HTTPException(status_code=500, detail=f"Redis 저장 오류: {str(e)}")


async def get_from_redis(key: str) -> str | None:
    try:
        return await redis_client.get(key)
    except Exception as e:
        logger.error(f"Redis 조회 오류 (Key: {key}): {e}")
        raise HTTPException(status_code=500, detail=f"Redis 조회 오류: {str(e)}")


async def delete_from_redis(key: str):
    try:
        await redis_client.delete(key)
    except Exception as e:
        logger.error(f"Redis 삭제 오류 (Key: {key}): {e}")
        raise HTTPException(status_code=500, detail=f"Redis 삭제 오류: {str(e)}")


# Redis 키 생성 함수
def get_redis_key_jti(jti: str) -> str:
    return f"jti:{jti}"


def get_redis_key_refresh_token(user_id: int) -> str:
    return f"refresh_token:{user_id}"


async def mark_jti_used(jti: str, expiry: int):
    try:
        await save_to_redis(f"jti:{jti}", "used", expiry)
    except Exception as e:
        logger.error(f"JTI 사용 마크 오류 (JTI: {jti}): {e}")
        raise HTTPException(status_code=500, detail="JTI 사용 처리 중 오류가 발생했습니다.")


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
