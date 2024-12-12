import logging

from fastapi import HTTPException

from src.config.database.redis import get_redis_cache

redis_client = get_redis_cache()

# TTL 설정
REFRESH_TOKEN_TTL = 7 * 24 * 3600  # 7일
JTI_TTL = 45 * 60  # 45분

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
    # return await redis_client.get(key)
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
