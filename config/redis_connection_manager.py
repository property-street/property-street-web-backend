from contextlib import asynccontextmanager
from redis.asyncio import Redis, ConnectionPool

from property_street_backend.config.settings import (
    DEBUG,
    DEV_REDIS_URL,
    PROD_REDIS_URL,
)

def get_redis_db_url():
    return DEV_REDIS_URL if DEBUG else PROD_REDIS_URL

redis_url = get_redis_db_url()
pool: ConnectionPool = ConnectionPool.from_url(
    redis_url, 
    decode_responses=True
)

def get_redis_from_pool() -> Redis:
    return Redis(connection_pool=pool)

@asynccontextmanager
async def get_redis_instance():
    redis = get_redis_from_pool()

    try:
        yield redis
    finally:
        await redis.aclose()

@asynccontextmanager
async def get_redis():
    redis = get_redis_from_pool()

    try:
        yield redis
    finally:
        await redis.aclose()
