import pytest, json
from sqlalchemy.future import select


from property_street_backend.app.models import (
    Asset, 
    Agent,
    AssetFeature, 
)
from property_street_backend.tests.activity.test_controller.test_objects import (
    feature_obj as payload,
)
from property_street_backend.tests.auth.test_create_agent import create_test_agent
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
        test_db = fixture_obj["db"]
        redis_client = fixture_obj["redis_client"]
        break

    try:
        expiry_seconds = 3

        # modify feature object to include an agent's id
        created_agent: Agent = await create_test_agent(test_db)
        payload[0]['db_table_id'] = created_agent.id
        
        # Process asset with features
        created_asset: Asset = await process_asset(
            data_to_be_processed=payload, 
            db = test_db,
            redis_client = redis_client,
            ttl_in_seconds = expiry_seconds,
        )

        asset_schema = AssetResponseSchema.model_validate(created_asset)
        asset_dict = asset_schema.model_dump()
        
        # Check the features
        assert created_asset.features is not None
        assert asset_schema.agent.first_name == created_agent.user.first_name
        
        # cache assertions
        # await assertions_after_caching(
        #     redis_client=redis_client,
        #     asset_id=created_asset.id,
        #     asset_data=asset_dict,
        #     expiry_seconds = expiry_seconds
        # )
    finally:
        await test_db.close()
        await redis_client.aclose()

