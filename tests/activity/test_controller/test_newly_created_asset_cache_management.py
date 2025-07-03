import pytest
import json
import asyncio
from redis.asyncio import Redis


from property_street_backend.app.controllers.activity.asset_routine_methods import (
    create_or_update_newly_created_asset_cache
)

# Mock inputs
hash_key = "newly_created_asset"
hset_key = "auto_category"


async def assertions_after_caching(
    redis_client: Redis,
    asset_id: int,
    asset_data: dict,
    expiry_seconds: int
):
    asset_data_str = json.dumps(asset_data)
    
    # Assert that the asset ID was added to the tracking set
    assert await redis_client.sismember(f"{hash_key}", asset_id)


    # Assert that the value of the newly_created_asset:{asset_id} matches asset_json
    cached_asset_str = await redis_client.get(f"{hash_key}:{asset_id}")
    assert cached_asset_str.decode() == asset_data_str

    # Assert that the asset_json is an entry in the hash set
    newly_created_asset_hset_field = hash_key
    auto_category = await redis_client.hget("auto_category", f"{newly_created_asset_hset_field}")
    assert auto_category is not None
    collection = json.loads(auto_category)
    assert collection[str(asset_id)] == asset_data

    # Wait for expiry 
    await asyncio.sleep(expiry_seconds + 3)

    # Assertions after expiry
    # Assert that the asset ID is no longer in the tracking set
    assert not await redis_client.sismember(hash_key, asset_id)

    # Assert that the set for the specific asset ID no longer exists
    assert not await redis_client.get(f"{hash_key}:{asset_id}")

    # Assert that the asset_json is removed from the hash set
    auto_category = await redis_client.hget(hset_key, hash_key)
    if auto_category:
        collection = json.loads(auto_category)
        assert str(asset_id) not in collection


async def finality_after_caching(
    redis_client: Redis,
    asset_id: int,
):
    # Cleanup to ensure no residual data in Redis
    await redis_client.delete(f"{hash_key}:{asset_id}")
    await redis_client.srem(hash_key, asset_id)
    auto_category = await redis_client.hget(hset_key, hash_key)
    if auto_category:
        collection = json.loads(auto_category)
        collection.pop(str(asset_id), None)
        if collection:
            await redis_client.hset(
                hset_key, hash_key, json.dumps(collection)
            )
        else:
            await redis_client.hdel(hset_key, hash_key)
 

@pytest.mark.asyncio
async def test_cache_newly_created_asset(client__fixture_with_prod_redis):
    expiry_seconds = 5
    # Connect to the Redis server
    client_gen = client__fixture_with_prod_redis
    client, redis_client = await client_gen.__anext__()

    asset_id = 12345
    asset_data = {"name": "Test Asset", "category": "Test Category"}
    asset_json = json.dumps(asset_data)

    try:
        # -*-*-*First call-*-*-*
        # Call the function
        await create_or_update_newly_created_asset_cache(
            asset_id=asset_id,
            asset_data=asset_data,
            redis_client=redis_client,
            expiry_seconds=expiry_seconds,
            newly_created = True,
        )

        # Assertions before expiry
        await assertions_after_caching(
            redis_client = redis_client,
            asset_data= asset_data,
            asset_json=asset_json,
            asset_id=asset_id,
        )


        # -*-*-*Second call-*-*-*
        await create_or_update_newly_created_asset_cache(
            asset_id=asset_id,
            asset_data=asset_data,
            redis_client=redis_client,
            expiry_seconds=expiry_seconds,
            newly_created = False,
        )
        # Assertions before expiry
        # Assert that the asset ID wasn't added to the tracking set
        assert not await redis_client.sismember(f"{hash_key}", asset_id)

        # Assert that the value of the newly_created_asset:{asset_id} is null
        assert not await redis_client.get(f"{hash_key}:{asset_id}")

        # Assert that the asset_json is an entry in the hash set
        auto_category = await redis_client.hget("auto_category", f"{hash_key}")
        loaded_auto_category = json.loads(auto_category)
        if isinstance(loaded_auto_category, dict):
            collection = json.loads(auto_category)
            assert not collection.get(str(asset_id))

        # waiting for expiry to avoid memory leaks


    finally:
        await finality_after_caching(
            redis_client,
            asset_id=asset_id,
        )