import redis
from contextlib import asynccontextmanager
from redis.asyncio import Redis, ConnectionPool

from property_street_backend.config import env_is_test
from property_street_backend.config.settings import (
    DEBUG,
    DEV_REDIS_URL,
    PROD_REDIS_URL,
    TEST_REDIS_URL,
)

def get_redis_url():
    if env_is_test():
        return TEST_REDIS_URL
    return DEV_REDIS_URL if DEBUG else PROD_REDIS_URL

redis_url = get_redis_url()
pool: ConnectionPool = ConnectionPool.from_url(
    redis_url, 
    decode_responses=True
)

def get_redis_from_pool() -> Redis:
    return Redis(connection_pool=pool)

@asynccontextmanager
async def get_redis_instance():
    redis = Redis(connection_pool=pool)
    try:
        yield redis
    finally:
        await redis.aclose()

@asynccontextmanager
async def get_redis():
    redis = Redis(connection_pool=pool)
    try:
        yield redis
    finally:
        await redis.aclose()


@asynccontextmanager
async def runtime_async_redis():
    URL = get_redis_url()
    pool: ConnectionPool = ConnectionPool.from_url(
        URL, decode_responses=True
    )
    redis = Redis(connection_pool=pool)
    try:
        yield redis
    finally:
        await redis.aclose()

#==============================
# Sync section
#==============================
def get_sync_redis() -> Redis:
    return redis.Redis.from_url(
        redis_url,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        health_check_interval=30,
    )