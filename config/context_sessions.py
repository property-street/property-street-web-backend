from redis.asyncio import Redis

from .postgres_connection_manager import get_postgres_instance
from .redis_connection_manager import get_redis_instance


async def get_db_based_on_context(**kwargs):
    # env = get_env()
    async for db in get_postgres_instance(**kwargs):
        yield db

async def get_redis_based_on_context(**kwargs):
    # env = get_env()
    async for redis_client in get_redis_instance(**kwargs):
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