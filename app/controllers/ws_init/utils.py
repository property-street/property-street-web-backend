from redis.asyncio import Redis

async def delete_pend_pool_when_empty(
    redis_client: Redis,
    pend_pool_key: str
):
    if await redis_client.exists(pend_pool_key):
        messages = await redis_client.hget(pend_pool_key, 'messages')
        notifications = await redis_client.hget(pend_pool_key, 'notifications')
        if not messages and not notifications:    
            await redis_client.delete(pend_pool_key)