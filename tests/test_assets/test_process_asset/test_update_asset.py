import pytest, json
from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession


from property_street_backend.app.controllers.auth.services import (
    fetch_access_token,
)
from property_street_backend.app.models import Asset, Agent
from property_street_backend.tests.test_assets.test_create_asset import (
    create_test_asset,
)
from property_street_backend.tests.auth.test_create_agent import create_test_agent
from property_street_backend.app.controllers.activity.agent_crud_processing import (
    process_asset,
)


@pytest.mark.asyncio
async def test_asset_update(client__fixture):
    # get the yield client objects
    async for fixture_obj in client__fixture:
        # extract the database entry
        test_db: AsyncSession = fixture_obj["db"]
        httpx_client: AsyncClient = fixture_obj["http_client"]
        break
    
    created_asset = await create_test_asset(
        db = test_db
    )


    update_obj = {
        1:{
            # Asset
            "db_delete": False,
            "db_table_id":created_asset.id,
            "db_table_name": "Asset",

            # fields
            "fields": {
                "title": "4 bedrooms flat",
                "status": "Rent",
                "category": "Condo",
                "description": "bulaba",
            },
        }
    }

        # fetch a token for the user
    tokenObj = fetch_access_token(user=created_asset.agent.user)

    # Define the payload for the request
    payload = {
        # 'tags_to_remove_object': {},
        'asset_data_to_process': update_obj,
    }

    # Generate an access token for authentication
    token = tokenObj['access_token']
    headers = {"Authorization": f"Bearer {token}"}

    # Make the request using the client provided by the fixture
    response = await httpx_client.post(
        "/assets/process-asset",
        json=payload,  # Use json instead of data for a JSON body
        headers=headers
    )
    updated_asset: Asset = response.json()
    
    # assertions
    asset_fields = update_obj[1]['fields']
    assert updated_asset is not None
    assert updated_asset['title'] == asset_fields['title']
    assert updated_asset['status'] == asset_fields['status']
    assert updated_asset['category'] == asset_fields['category']
    assert updated_asset['description'] == asset_fields['description']