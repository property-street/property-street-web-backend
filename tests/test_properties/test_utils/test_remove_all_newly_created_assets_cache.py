import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy import select
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import Asset
from app.controllers.auth.services import fetch_access_token
from property_street_backend.app.controllers.activity import (
    auto_category_hset_key,
    newly_created_asset_set_key, 
)
from property_street_backend.tests.auth.test_create_agent import create_test_agent
from property_street_backend.app.controllers.activity.asset_routine_methods import (
    remove_all_newly_created_assets_cache,
    create_or_update_newly_created_asset_cache,
)
from property_street_backend.app.controllers.assets.schemas import PropertyResponseSchema
from property_street_backend.tests.test_properties.test_processing import property_payload
from property_street_backend.app.controllers.assets.relationship_handler import apply_model



@pytest.mark.asyncio
async def test_remove_all_newly_created_assets_cache(client__fixture):
    expiry_seconds = 10
    newly_created_hash_key = newly_created_asset_set_key

    redis_client: Redis = client__fixture["redis_client"]
    test_db: AsyncSession = client__fixture["db"]

    agent = await create_test_agent(test_db)
    token = fetch_access_token(user=agent)["access_token"]
    headers = {"Authorization": f"Bearer {token}"}


    # ───────────── Create & cache multiple assets ─────────────
    assets = []
    amount = 3
    for _ in range(amount):
        payload = property_payload(agent.id)
        asset = await apply_model(Asset, test_db, payload)
        assert asset is not None
        await asyncio.sleep(1)

        asset_dict = PropertyResponseSchema.model_validate(
            asset
        ).model_dump()

        await create_or_update_newly_created_asset_cache(
            asset_id=asset.id,
            asset_data=asset_dict,
            redis_client=redis_client,
            expiry_seconds=expiry_seconds,
            newly_created=True,
        )

    # Sanity check: SET has entries
    members = await redis_client.smembers(newly_created_hash_key)
    assert len(members) == amount

    # ───────────── Bulk removal ─────────────
    await remove_all_newly_created_assets_cache(redis_client)

    # ───────────── Assertions ─────────────

    # 1️⃣ Tracking SET should be gone
    exists = await redis_client.exists(newly_created_hash_key)
    assert exists == 0

    # 2️⃣ Auto-category HSET field should be gone
    hset_value = await redis_client.hget(
        auto_category_hset_key,
        newly_created_hash_key
    )
    assert hset_value is None

    # 3️⃣ Per-asset keys should be gone
    for asset in assets:
        asset_key = f"{newly_created_hash_key}:{asset.id}"
        assert await redis_client.exists(asset_key) == 0
