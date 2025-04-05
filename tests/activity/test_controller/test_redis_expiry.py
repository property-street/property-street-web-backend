import json
import pytest
import asyncio

from property_street_backend.config.settings import REDIS_CACHE_DB

@pytest.mark.asyncio
async def test_redis_expiry(client__fixture_with_prod_redis):
    # Fetch the client generator
    client_gen = client__fixture_with_prod_redis
    client, redis_client = await client_gen.__anext__()

    response = await client.get("/")
    assert response.status_code == 200

    # Step 1: Add the integer `1` to the set `newly_created_asset`
    await redis_client.sadd('newly_created_asset', 1)
    # Step 2: Retrieve and verify that the integer `1` exists in the set
    assert await redis_client.sismember('newly_created_asset', 1)

    # Step 3: Create another set with the key `newly_created_asset:1`
    await redis_client.sadd('newly_created_asset:1', "This is a test value")
    # Step 4: Set an expiry on the set `newly_created_asset:1` (1 second)
    await redis_client.expire('newly_created_asset:1', 1)

    # Step 5: Wait for 2 seconds to ensure the key expires
    await asyncio.sleep(2)

    # Verify if the key `newly_created_asset:1` has expired
    assert not await redis_client.exists('newly_created_asset:1')

    # Step 6: Check if the integer `1` is still a member of `newly_created_asset`
    assert not await redis_client.sismember('newly_created_asset', 1)

    asset_id = 12345
    asset_data = {
        "name": "Test Asset", 
        "category": "Test Category",
    }

    # test deletion of specific set
    specific_set = f'newly_created_asset:{asset_id}'
    await redis_client.sadd(specific_set, "This is a test value")
    await redis_client.delete(specific_set)
    assert not await redis_client.exists(specific_set)

    # test hset insertion and deletion
    hash_key = "auto_category"
    field = "newly_created_asset"
    # insert data to the hset
    await redis_client.hset(
        hash_key, 
        field, 
        json.dumps({asset_id:asset_data})
    )
    # get the just inserted data 
    auto_category = await redis_client.hget(hash_key, field)
    # convert it to a python object
    collection = json.loads(auto_category)
    key = str(asset_id)
    assert collection.pop(key) == asset_data
    # delete the newly_created_asset entry
    await redis_client.hdel(hash_key, field)
    # assert that the entry is null
    assert not await redis_client.hget(hash_key, field)