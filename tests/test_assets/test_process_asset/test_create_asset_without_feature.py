import pytest, json
from httpx import AsyncClient
from sqlalchemy.future import select
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.config.settings import TEST_NEWLY_CREATED_ASSET_TTL
from property_street_backend.app.models import (
    Asset, 
    AssetFeature, 
    User,
)
from property_street_backend.app.controllers.assets.schemas import (
    AssetResponseSchema
)
from property_street_backend.app.controllers.auth.services import (
    fetch_access_token,
)
from property_street_backend.tests.activity.test_controller.test_objects import (
    no_feature_obj as payload,
)
from property_street_backend.tests.auth.test_user_creation import create_test_user
from property_street_backend.tests.activity.test_controller.test_newly_created_asset_cache_management import (
    assertions_after_caching,
)


@pytest.mark.asyncio
async def test_create_asset_without_feature(sessions_with_cache_expiry_event_fixture):
    # get the yield client objects
    async for fixture_obj in sessions_with_cache_expiry_event_fixture:
        test_db: AsyncSession = fixture_obj["db"]
        redis_client: Redis = fixture_obj["redis_client"]
        httpx_client: AsyncClient = fixture_obj["http_client"]
        break

    try:
        # modify feature object to include an agent's id
        created_agent: User = await create_test_user(test_db)

        # Generate an access token for authentication
        token_obj = fetch_access_token(user=created_agent)
        token = token_obj['access_token']
        headers = {"Authorization": f"Bearer {token}"}
        
        json_data = {
            "asset_data_to_process": payload
        }
        # Process asset with features
        response = await httpx_client.post(
            "/assets/process-asset", 
            headers = headers,
            json = json_data,
        )

        created_asset = response.json()
        asset_schema = AssetResponseSchema.model_validate(created_asset)
        asset_dict = asset_schema.model_dump()
        tags = asset_dict['tags'] 
        assert len(tags) >= 1
        assert tags[0]['name']
        assert tags[1]['name']
        
        
        # cache assertions
        await assertions_after_caching(
            redis_client=redis_client,
            asset_id=created_asset['id'],
            asset_data=asset_dict,
            expiry_seconds = TEST_NEWLY_CREATED_ASSET_TTL
        )
    finally:
        await test_db.close()
        await redis_client.aclose()

