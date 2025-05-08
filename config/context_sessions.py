import os
from redis.asyncio import Redis

from .postgres_connection_manager import get_postgres_instance
from .redis_connection_manager import get_redis_instance

def get_env():
    # environment retrieval based on context
    TEST_ENV = os.getenv("TEST_ENV")
    env = 'test' if TEST_ENV else 'prod'
    return env

async def get_db_based_on_context(**kwargs):
    env = get_env()
    async for test_db in get_postgres_instance(env,**kwargs):
        yield test_db

async def get_redis_based_on_context(**kwargs):
    env = get_env()
    async for redis_client in get_redis_instance(env, **kwargs):
        yield redis_client

async def acquire_redis_lock(redis_client: Redis, lock_key: str, ex: int):
    """Acquire a lock to ensure only one instance runs."""
    return await redis_client.set(
        lock_key, 
        "locked", 
        ex=ex,
        nx=True
    )

async def release_redis_lock(redis_client: Redis, lock_key: str,):
    """Release the lock after task completion."""
    await redis_client.delete(lock_key)