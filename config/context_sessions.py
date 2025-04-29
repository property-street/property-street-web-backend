import os
from redis.asyncio import Redis

from property_street_backend.app.database import get_db
from property_street_backend.app.initiator import get_redis
from property_street_backend.tests.initiator import get_test_db, get_test_redis

def get_env():
    # environment retrieval based on context
    TEST_ENV = os.getenv("TEST_ENV")
    env = 'test' if TEST_ENV else 'prod'
    return env

async def get_db_based_on_context():
    env = get_env()
    if env == 'test':
        async for db in get_test_db(metadata_test_routine=False):
            break
    else:
        async for db in get_db():
            break
    return db

async def get_redis_based_on_context():
    env = get_env()
    if env == 'test':
        async for redis_client in get_test_redis():
            break
    else:
        async for redis_client in get_redis():
            break
    return redis_client

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