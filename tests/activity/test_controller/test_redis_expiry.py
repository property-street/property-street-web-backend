import pytest
import asyncio
from redis.asyncio import Redis

from property_street_backend.app.controllers.cache_expiration import cache_expiry_initializer 
from property_street_backend.app.controllers.cache_expiration.expiry_pubsub_listener import expiry_pubsub_loop_entered 


@pytest.mark.asyncio
async def test_redis_expiry(sessions_fixture):
    listener_task = None
    stop_event = None

    try:
        async for fixture_map in sessions_fixture:
            redis_client: Redis
            redis_client = fixture_map['redis_client']

        # ✅ FIXED: Properly await the initializer
        (
            listener_task, 
            stop_event, 
            _
        ) = await cache_expiry_initializer(redis_client)

        # ✅ Poll until the listener loop is confirmed to be active
        for _ in range(60):
            loop_entered = await redis_client.exists(expiry_pubsub_loop_entered)
            if loop_entered:
                break
            await asyncio.sleep(0.1)  # prevent tight loop

        if not loop_entered:
            raise Exception("Expiry pubsub listener never started.")

        await redis_client.sadd('newly_created_asset', 1)
        assert await redis_client.sismember('newly_created_asset', 1)

        await redis_client.set('newly_created_asset:1', "value", ex=1)

        await asyncio.sleep(2)  # allow expiry to trigger

        assert not await redis_client.exists('newly_created_asset:1')
        assert not await redis_client.sismember('newly_created_asset', 1)

    finally:
        if stop_event:
            stop_event.set()
        if listener_task:
            await listener_task
