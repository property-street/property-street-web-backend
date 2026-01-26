import pytest
import json
import asyncio
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import (
    User, 
    Asset,
)
from tests.test_properties.test_processing.test_apply_model import create_test_asset
from property_street_backend.app.controllers.activity.asset_routine_methods import (
    newly_created_hash_key,
    auto_category_hset_key,
)
from property_street_backend.app.controllers.activity.asset_routine_methods import (
    create_or_update_newly_created_asset_cache,
    remove_asset_from_newly_created_asset_cache
)
from property_street_backend.app.controllers.assets.schemas import PropertyResponseSchema


hash_key = newly_created_hash_key
hset_key = auto_category_hset_key

async def assertions_after_caching(
    redis_client: Redis,
    asset_id: int,
    expiry_seconds: int,
    expiry_loop_activated: bool = False
):

    asset_key = f'{hash_key}:{asset_id}'

    # Assert that the asset ID was added to the tracking set
    assert await redis_client.sismember(f"{hash_key}", asset_id)


    # Assert that the value of the `newly_created_asset:{asset_id}` matches asset_json
    assert await redis_client.get(asset_key)

    # Assert that the asset_json is an entry in the hash set
    hset_field = hash_key
    auto_category = await redis_client.hget(hset_key, hset_field)
    assert auto_category is not None
    collection: dict = json.loads(auto_category)
    assert collection.get(str(asset_id))

    if expiry_loop_activated:
        # Wait for expiry 
        await asyncio.sleep(expiry_seconds + 3)

        # Assertions after expiry
        # Assert that the asset ID is no longer in the tracking set
        assert not await redis_client.sismember(hash_key, asset_id)

        # Assert that the set for the specific asset ID no longer exists
        assert not await redis_client.get(asset_key)

        # Assert that the asset_json is removed from the hash set
        auto_category = await redis_client.hget(hset_key, hset_field)
        if auto_category:
            collection = json.loads(auto_category)
            assert str(asset_id) not in collection

async def assertions_after_newly_created_cache_removal(redis_client: Redis, property_id: int):
    asset_key = f"{newly_created_hash_key}:{property_id}"

    # 1️⃣ Per-asset cache key should be gone
    exists = await redis_client.exists(asset_key)
    assert exists == 0

    # 2️⃣ Property ID should be removed from tracking SET
    assert not await redis_client.sismember(
        newly_created_hash_key,
        property_id
    )

    # 3️⃣ Property should be removed from auto-category HSET JSON
    hset_value = await redis_client.hget(
        auto_category_hset_key,
        newly_created_hash_key
    )

    if hset_value:
        loaded_assets = json.loads(hset_value)
        assert str(property_id) not in loaded_assets
    else:
        # Field deleted entirely is also valid
        assert hset_value is None


async def finality_after_caching(
    redis_client: Redis, asset_id: int,
):
    pass 

@pytest.mark.asyncio
async def test_newly_created_caching(client__fixture):
    expiry_seconds = 5

    redis_client: Redis = client__fixture["redis_client"]
    test_db: AsyncSession = client__fixture["db"]

    property: Asset = await create_test_asset(test_db)
    property_id = property.id

    property_dict = PropertyResponseSchema.model_validate(
        property
    ).model_dump()

    # ───────────── First call: cache asset ─────────────
    await create_or_update_newly_created_asset_cache(
        asset_id=property_id,
        asset_data=property_dict,
        redis_client=redis_client,
        expiry_seconds=expiry_seconds,
        newly_created=True,
    )

    # Assert cache exists
    await assertions_after_caching(
        redis_client, property_id, expiry_seconds
    )

    # ───────────── Second call: remove asset ─────────────
    await remove_asset_from_newly_created_asset_cache(
        property_id,
        redis_client
    )

    # ───────────── Removal assertions ─────────────
    await assertions_after_newly_created_cache_removal(
        redis_client, property_id
    )
