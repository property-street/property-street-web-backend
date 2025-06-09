import pytest, json
from sqlalchemy.future import select


from property_street_backend.app.models import (
    Asset, 
    AssetFeature, 
)
from property_street_backend.app.schemas.asset_schemas import (
    AssetSchema
)
from property_street_backend.tests.activity.test_controller.test_objects import (
    feature_obj as payload,
)
from property_street_backend.tests.auth.test_create_agent import create_test_agent
from property_street_backend.app.controllers.activity.agent_crud_processing import (
    process_asset,
)
from property_street_backend.tests.activity.test_controller.test_newly_created_asset_cache_management import (
    expiry_seconds,
    finality_after_caching, 
    assertions_after_caching,
)


@pytest.mark.asyncio
async def test_create_asset_with_feature(client__fixture):
    # get the yield client objects
    fixture_obj: dict = await anext(client__fixture)
    test_db = fixture_obj.get("db")
    redis_client =  await fixture_obj.get("redis_client")

    created_asset = None

    try:
        # modify feature object to include an agent's id
        created_agent = await create_test_agent(test_db)
        payload[0]['db_table_id'] = created_agent.id
        
        # Process asset with features
        await process_asset(
            data_to_be_processed=payload, 
            db = test_db,
            redis_client = redis_client,
            newly_created = True,
            ttl_in_seconds = expiry_seconds,
        )

        # Fetch the created asset from the database
        result = await test_db.execute(select(Asset).filter(Asset.title == payload[4]['fields']['title']))
        created_asset = result.scalars().first()
        # Assertions
        assert created_asset is not None
        assert created_asset.title == payload[4]['fields']['title']
        assert created_asset.has_features is True

        asset_schema = AssetSchema.model_validate(created_asset)
        asset_dict = asset_schema.model_dump()
        
        # cache assertions
        # await assertions_after_caching(
        #     redis_client=redis_client,
        #     asset_id=created_asset.id,
        #     asset_data=asset_dict,
        # )


        # Check the features
        result = await test_db.execute(select(AssetFeature).filter(AssetFeature.asset_id == created_asset.id))
        asset_feature = result.scalars().first()
        assert asset_feature is not None
    finally:
        # cache finality
        if created_asset:
            await finality_after_caching(
                redis_client = redis_client,
                asset_id = created_asset.id
            )
        await test_db.close()
        await redis_client.aclose()

