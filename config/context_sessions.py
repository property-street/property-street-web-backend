from redis.asyncio import Redis


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