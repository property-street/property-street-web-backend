import pytest

from property_street_backend.app.models import (
    CloudImageDetail,
)
from property_street_backend.app.controllers.auth import (
    fetched_access_token,
)
from property_street_backend.tests.activity.test_controller.test_asset_creation import (
    create_test_agent
)


import pytest

@pytest.mark.asyncio
async def test_user_ui_metadata_retrieval(client__fixture):
    # Extract the fixture object
    fixture_obj = await client__fixture.__anext__()
    test_db = fixture_obj.get("db")
    client = fixture_obj.get("http_client")
    """
    Test the /activity/assets/latest endpoint to ensure it fetches
    up to 100 latest assets with the correct structure.
    """

    # Create a test agent and user
    test_agent = await create_test_agent(db=test_db)
    test_user = test_agent.user

    # profile avatar cloud image details
    # assigning it to the user and committing
    profile_avatar_details = {
        "cloud_asset_id": "cloud_asset_id",
        "format": "format",
        "bytes": 1500,
        "height": 1620,
        "secure_url": "https://example.com/silly.png",
        "width": 1480,
        "public_id": "avatar_public_id"
    }
    test_user.profile_avatar = CloudImageDetail(**profile_avatar_details)
    test_db.add(test_user)
    await test_db.commit()

    # Fetch a token for the user
    token_obj = fetched_access_token(user=test_user)
    token = token_obj["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Perform the GET request to fetch the latest assets
    # Validate response status
    response = await client.get("/activity/user-ui-metadata", headers=headers)
    assert response.status_code == 200
    data = response.json()

    # refresh user
    # Validate response structure
    await test_db.refresh(test_user)
    assert test_user.first_name == data.get('first_name')
    assert test_user.id == data.get('user_id')
    assert test_user.profile_avatar.secure_url == data.get('profile_avatar_url')
    assert data.get('client_is_agent')
    assert data.get('is_authenticated')


    #**# fetch without authentication
    headers = {"Authorization": f"Bearer "}
    response = await client.get("/activity/user-ui-metadata", headers=headers)
    
    # Validate response status
    # Validate response structure
    assert response.status_code == 200
    data = response.json()
    assert None == data.get('profile_avatar_url')
    assert None == data.get('first_name')
    assert None == data.get('user_id')
    assert None == data.get('client_is_agent')
    assert not data.get('is_authenticated')
