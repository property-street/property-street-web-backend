import pytest
from sqlalchemy.future import select

from property_street_backend.app.controllers.auth import (
    fetched_access_token,
    create_user
)
from property_street_backend.app.schemas.auth_schemas import (
    UserRegistrationSchema
)
from property_street_backend.tests.activity.test_controller.test_get_agent_assets import (
    create_asset_and_component
)




@pytest.mark.asyncio
async def test_agent_asset_retrieval(client__fixture_with_onlyDB_fixture: tuple):
    # Fetch the client generator
    client_gen = client__fixture_with_onlyDB_fixture
    # Get the yielded client object
    client, test_db = await client_gen.__anext__()

    user_data = UserRegistrationSchema(
        email="agent@example.com",
        username="agentuser",
        password="password123"
    )

    # Call the create_user function
    user = await create_user(test_db, user_data)

    # make the user an agent
    await user.become_agent(
        session = test_db
    )

    # call the create asset and component function
    await create_asset_and_component(
        db = test_db,
        agent = user.agent_profile
    )

    # fetch a token for the user
    tokenObj = fetched_access_token(user=user)

    # Generate an access token for authentication
    token = tokenObj['access_token']
    # headers = {"Authorization": f"Bearer {token}"}

    # Make the request using the client provided by the fixture
    response = await client.get(
        "/activity/fetch_agent_assets",
        headers = {"Authorization": f"Bearer {token}"},
    )
    
    # Assertions
    assert response.status_code == 200
    json_response = response.json()
    assets_data = json_response.get('assets_data')
    grouped_cloud_details = json_response.get('grouped_cloud_details')
    assert isinstance((assets_data and grouped_cloud_details), dict)