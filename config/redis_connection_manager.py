from contextlib import asynccontextmanager
from redis.asyncio import Redis, ConnectionPool

from . import get_env
from property_street_backend.config.settings import (
    REDIS_HOST,
    TEST_REDIS_CACHE_DB,
    PROD_REDIS_CACHE_DB,
)

def get_redis_db_url():
    env = get_env()
    env_is_test = env == 'test'
    db = TEST_REDIS_CACHE_DB if env_is_test else PROD_REDIS_CACHE_DB
    return f"redis://{REDIS_HOST}:6379/{db}"

def get_redis_from_pool() -> Redis:
    redis_url = get_redis_db_url()
    pool = ConnectionPool.from_url(redis_url)
    return Redis(connection_pool=pool, decode_responses=True)

@asynccontextmanager
async def get_redis_instance():
    redis = get_redis_from_pool()

    try:
        yield redis
    finally:
        await redis.aclose()
