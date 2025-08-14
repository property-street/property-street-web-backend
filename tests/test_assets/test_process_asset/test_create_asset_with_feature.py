import pytest
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import (
    User,
    Asset, 
)
from property_street_backend.tests.activity.test_controller.test_objects import (
    feature_obj as payload,
)
from property_street_backend.tests.auth.test_user_creation import create_test_user
from property_street_backend.app.controllers.activity.agent_crud_processing import (
    process_asset,
)
from property_street_backend.app.controllers.assets.schemas import AssetResponseSchema
from property_street_backend.tests.activity.test_controller.test_newly_created_asset_cache_management import (
    assertions_after_caching,
)


@pytest.mark.asyncio
async def test_create_asset_with_feature(sessions_with_cache_expiry_event_fixture):
    # get the yield client objects
    async for fixture_obj in sessions_with_cache_expiry_event_fixture:
        test_db: AsyncSession = fixture_obj["db"]
        redis_client: Redis = fixture_obj["redis_client"]
        break

    try:
        expiry_seconds = 3

        # modify feature object to include an agent's id
        created_agent: User = await create_test_user(test_db)
        
        # Process asset with features
        created_asset: Asset = await process_asset(
            data_to_be_processed=payload, 
            db = test_db,
            redis_client = redis_client,
            ttl_in_seconds = expiry_seconds,
            agent = created_agent
        )

        asset_schema = AssetResponseSchema.model_validate(created_asset)
        asset_dict = asset_schema.model_dump()
        tags = asset_dict['tags'] 
        assert len(tags) == 2
        assert tags[0]['name']
        assert tags[1]['name']
        
        # Check the features
        assert created_asset.features is not None
        assert asset_schema.agent.username == created_agent.username
        
        # cache assertions
        await assertions_after_caching(
            redis_client=redis_client,
            asset_id=created_asset.id,
            asset_data=asset_dict,
            expiry_seconds = expiry_seconds
        )
    finally:
        await test_db.close()
        await redis_client.aclose()

