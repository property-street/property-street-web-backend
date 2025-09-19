import pytest, json, asyncio
from property_street_backend.app.models import Asset
from property_street_backend.app.schemas.asset_schemas import AssetSchema
from property_street_backend.app.controllers.search.search_string_processor import (
    process_search_entries
)
from property_street_backend.tests.activity.test_controller.test_asset_creation import (
    create_test_asset,
    create_test_agent,
)

trending_searches_zset_key = "trending_searches"

@pytest.mark.asyncio
async def test_process_search_entries_when_response_is_in_db(client__fixture):
    cache_key = ""
    try:
        fixture_obj = await client__fixture.__anext__()
        prod_redis_client = fixture_obj.get("prod_redis_client")
        test_db = fixture_obj.get("db")

        # Test input
        expiry_seconds = 2
        new_asset_category = "apartment"
        new_asset_title = "2 bedroom apartment"
        entries = ["2 bedroom:none", f"{new_asset_category}:category"]

        # Create test agent and asset
        created_agent = await create_test_agent(test_db)
        assert created_agent is not None
        created_asset = await create_test_asset(test_db, created_agent.id)
        assert created_asset is not None
        created_asset.title = new_asset_title
        created_asset.category = new_asset_category
        test_db.add(created_asset)
        await test_db.commit()

        # Call the process_search_entries function
        result = await process_search_entries(
            entries=entries,
            redis_client=prod_redis_client,
            db_session=test_db,
            expiry_seconds=expiry_seconds
        )

        # Assert that the result is not empty and matches the test data
        assert len(result) > 0
        first_match = result[0] if isinstance(result[0], Asset) else AssetSchema(**result[0])
        assert first_match.category == created_asset.category

        # Verify the cache entry exists
        cache_key = f"recent_{new_asset_category}"
        assert await prod_redis_client.exists(cache_key)

        # Wait for the cache entry to expire and assert it no longer exists
        for _ in range(5):
            if not await prod_redis_client.exists(cache_key):
                break
            await asyncio.sleep(1)
        assert not await prod_redis_client.exists(cache_key)

    finally:
        # Cleanup Redis keys
        await prod_redis_client.delete(cache_key)
        await prod_redis_client.delete(trending_searches_zset_key)

