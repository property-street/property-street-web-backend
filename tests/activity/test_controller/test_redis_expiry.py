import pytest
import asyncio
from redis.asyncio import Redis

from property_street_backend.app.controllers.cache_expiration import cache_expiry_initializer 


@pytest.mark.asyncio
async def test_redis_expiry(sessions_with_cache_expiry_event_fixture):

    async for fixture_map in sessions_with_cache_expiry_event_fixture:
        redis_client: Redis
        redis_client = fixture_map['redis_client']

    await redis_client.sadd('newly_created_asset', 1)
    assert await redis_client.sismember('newly_created_asset', 1)

    await redis_client.set('newly_created_asset:1', "value", ex=1)

    await asyncio.sleep(3)  # allow expiry to trigger; adjust as needed

    assert not await redis_client.exists('newly_created_asset:1')
    assert not await redis_client.sismember('newly_created_asset', 1)

