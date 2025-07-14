import pytest, json
from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import (
    User,
    Asset,
    Agent,
)
from property_street_backend.app.controllers.auth.services import (
    fetched_access_token,
)
from property_street_backend.app.controllers.assets.schemas import (
    AssetSchema,
    AssetFetchResponseSchema
)
from property_street_backend.config.settings import TEST_NEWLY_CREATED_ASSET_TTL
from property_street_backend.tests.activity.test_controller.test_objects import (
    feature_obj,
)
from property_street_backend.tests.auth.test_create_agent import create_test_agent
from property_street_backend.tests.activity.test_controller.test_newly_created_asset_cache_management import (
    assertions_after_caching,
)



@pytest.mark.asyncio
async def test_upload_asset(
    sessions_with_cache_expiry_event_fixture
):
    # Fetch the client generator
    async for fixture_obj in sessions_with_cache_expiry_event_fixture:
        # Get the yielded client object
        http_client: AsyncClient = fixture_obj['http_client'] 
        redis_client: Redis = fixture_obj['redis_client'] 
        test_db: AsyncSession = fixture_obj['db']
        break    

    # modify feature object to include an agent's id
    created_agent: Agent = await create_test_agent(test_db)
    feature_obj[0]['db_table_id'] = created_agent.id

    # fetch the test user
    result = await test_db.execute(
        select(User).filter(
        User.agent_profile_id == created_agent.id
    ))
    agent_user = result.scalars().first()

    # assert that the agent_user agent_profile id is 1
    assert agent_user.agent_profile_id == 1
    
    # fetch a token for the user
    tokenObj = fetched_access_token(user=agent_user)

    # Define the payload for the request
    payload = {
        # 'tags_to_remove_object': {},
        'asset_data_to_process': feature_obj,
    }

    # Generate an access token for authentication
    token = tokenObj['access_token']
    headers = {"Authorization": f"Bearer {token}"}

    # Make the request using the client provided by the fixture
    response = await http_client.post(
        "/assets/process-asset",
        json=payload,  # Use json instead of data for a JSON body
        headers=headers
    )
    
    # Assertions
    assert response.status_code == 200
    response_data = response.json()['data']
    schematized_response_data = AssetFetchResponseSchema.model_validate(response_data)
    
    # cache assertions
    result = await test_db.execute(
        select(Asset).filter(
        Asset.id == schematized_response_data.id
    ))
    created_asset = result.scalars().first()
    schematized_asset = AssetSchema.model_validate(created_asset)
    schematized_asset_to_dict = schematized_asset.model_dump()
    await assertions_after_caching(
        redis_client = redis_client,
        asset_id = created_asset.id,
        asset_data = schematized_asset_to_dict,
        expiry_seconds = TEST_NEWLY_CREATED_ASSET_TTL
    )