import pytest
from sqlalchemy.future import select

from property_street_backend.app.models import (
    User,
)
from property_street_backend.tests.activity.test_controller.test_objects import (
    feature_obj,
)
from property_street_backend.tests.auth.test_create_agent import create_test_agent
from property_street_backend.app.controllers.auth.services import fetch_access_token
from property_street_backend.tests.test_assets.test_create_asset import create_test_asset



@pytest.mark.asyncio
async def test_asset_update_with_auth(client__fixture_with_onlyDB_fixture: tuple):
    # Fetch the client generator
    client_gen = client__fixture_with_onlyDB_fixture
    # Get the yielded client object
    client, test_db = await client_gen.__anext__()


    created_asset = await create_test_asset(
        db = test_db,
    )

    update_obj = {
        1: {
            "db_table_id": -1,
            "db_delete": False,
            "db_table_name": "Tag",
            "fields": {
                "name": "1 bed"
                }
        },
        2: {
            "db_table_id": -1,
            "db_delete": False,
            "db_table_name": "Tag",
            "fields": {
                "name": "condo"
            }
        },
        3: {
            "db_table_id": created_asset.id,
            "db_table_name": "Asset",
            "db_delete": False,
            "fields": {
            "relationship": {
                "cloud_images": [],
                "tags": [1,2]
            },
            "status": "Lease",
            "amount": "500000",
            "category": "Peng house",
            "lease_duration": "12 months (1 year)"
            }
        }
    }
    tags_to_remove_object = {
        "asset_id": created_asset.id,
        "tag_ids": [tag.id for tag in created_asset.tags],
    }

    # Define the payload for the request
    payload = {
        'asset_data_to_process': update_obj,
        'tags_to_remove_object': tags_to_remove_object,
    }

    # fetch the test user
    result = await test_db.execute(
        select(User).filter(User.username == agent.user.username)
    )
    agent_user = result.scalars().first()

    # fetch a token for the user
    tokenObj = fetch_access_token(user=agent_user)

    # Generate an access token for authentication
    token = tokenObj['access_token']
    headers = {"Authorization": f"Bearer {token}"}

    # Make the request using the client provided by the fixture
    response = await client.post(
        "/activity/process_asset",
        json=payload,  # Use json instead of data for a JSON body
        headers=headers
    )
    
    # Assertions
    assert response.status_code == 200
    json_response = response.json()
    len_processed = json_response.get("processed")
    assert isinstance(len_processed, int)