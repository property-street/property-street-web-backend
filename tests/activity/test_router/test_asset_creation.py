import pytest, json
from sqlalchemy.future import select

from property_street_backend.app.models import (
    User,
    Asset,
)
from property_street_backend.app.controllers.auth import (
    fetched_access_token,
)
from property_street_backend.app.schemas.asset_schemas import (
    AssetSchema
)
from property_street_backend.tests.activity.test_controller.test_objects import (
    feature_obj,
)
from property_street_backend.tests.activity.test_controller.test_asset_management_phase1 import (
    add_created_clientId_to_payload,
)
from property_street_backend.tests.activity.test_controller.test_newly_created_asset_cache_management import (
    expiry_seconds,
    finality_after_caching, 
    assertions_after_caching,
)



@pytest.mark.asyncio
async def test_asset_upload_with_auth(
    client__fixture_with_onlyDB_fixture: tuple,
    prod_redis_client__fixture
):
    # Fetch the client generator
    client_gen = client__fixture_with_onlyDB_fixture
    # Get the yielded client object
    client, test_db = await client_gen.__anext__()
    
    # fetch the client fixture
    redis_client =  await prod_redis_client__fixture

    try:
        # Add the created client ID to the payload (assuming feature_obj is predefined)
        await add_created_clientId_to_payload(
            db=test_db,
            payload=feature_obj
        )

        # fetch the test user
        result = await test_db.execute(select(User).filter(User.username == "agentuser"))
        agent_user = result.scalars().first()

        # assert that the agent_user agent_profile id is 1
        assert agent_user.agent_profile_id == 1
        
        # fetch a token for the user
        tokenObj = fetched_access_token(user=agent_user)

        # Define the payload for the request
        payload = {
            'tags_to_remove_object': {},
            'asset_data_to_process': feature_obj,
            "newly_created": True,
            "ttl": expiry_seconds,
        }

        # Generate an access token for authentication
        token = tokenObj['access_token']
        headers = {"Authorization": f"Bearer {token}"}

        # Make the request using the client provided by the fixture
        response = await client.post(
            "/activity/process_asset",
            json=payload,  # Use json instead of data for a JSON body
            headers=headers
        )
                # Fetch the created asset from the database
        
        # Assertions
        result = await test_db.execute(select(Asset).filter(Asset.title == feature_obj[4]['fields']['title']))
        created_asset = result.scalars().first()
        asset_schema = AssetSchema.model_validate(created_asset)
        asset_cache_object = json.dumps(
            asset_schema.model_dump()
        )
        asset_json = json.dumps(asset_cache_object)

        # cache assertions
        await assertions_after_caching(
            redis_client=redis_client,
            asset_id=created_asset.id,
            asset_data=asset_cache_object,
            asset_json = asset_json,
        )

        assert response.status_code == 200
        json_response = response.json()
        len_processed = json_response.get("processed")
        assert isinstance(len_processed, int)

    finally:
        # cache finality
        await finality_after_caching(
            redis_client = redis_client,
            asset_id = created_asset.id
        )