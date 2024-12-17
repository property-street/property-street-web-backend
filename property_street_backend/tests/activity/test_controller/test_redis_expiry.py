import time
import pytest
import redis.asyncio as redis

from property_street_backend.config.settings import REDIS_CACHE_DB

@pytest.mark.asyncio
async def test_redis_expiry():
    # Connect to the Redis server
    redis_client = redis.Redis(
        host='localhost', 
        port=6379, 
        db=REDIS_CACHE_DB,
        decode_responses=True
    )

    # Step 1: Add the integer `1` to the set `newly_created_asset`
    await redis_client.sadd('newly_created_asset', 1)

    # Step 2: Retrieve and verify that the integer `1` exists in the set
    assert await redis_client.sismember('newly_created_asset', 1)

    # Step 3: Create another set with the key `newly_created_asset:1`
    await redis_client.sadd('newly_created_asset:1', "This is a test value")

    # Step 4: Set an expiry on the set `newly_created_asset:1` (1 second)
    await redis_client.expire('newly_created_asset:1', 1)

    # Step 5: Wait for 2 seconds to ensure the key expires
    time.sleep(2)

    # Verify if the key `newly_created_asset:1` has expired
    assert not await redis_client.exists('newly_created_asset:1')

    # Step 6: Check if the integer `1` is still a member of `newly_created_asset`
    assert not await redis_client.sismember('newly_created_asset', 1)
