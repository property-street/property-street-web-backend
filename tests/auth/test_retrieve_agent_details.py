import pytest

from property_street_backend.app.controllers.auth.services import (
    fetched_access_token,
    create_user
)
from property_street_backend.app.schemas.auth_schemas import (
    UserRegistrationSchema
)



@pytest.mark.asyncio
async def test_retrieve_user_details(client__fixture_with_onlyDB_fixture: tuple):
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
    user = await create_user(
        db = test_db, 
        user_data = user_data
    )

    # await the user to agent change
    await user.become_agent(
        session = test_db
    )

    agent = user.agent_profile

    # fetch a token fors the user
    tokenObj = fetched_access_token(user=user)

    # Generate an access token for authentication
    token = tokenObj['access_token']
    # headers = {"Authorization": f"Bearer {token}"}

    # Make the request using the client provided by the fixture
    response = await client.get(
        "/auth/retrieve-agent-details",
        headers = {"Authorization": f"Bearer {token}"},
    )
    
    # Assertions
    assert response.status_code == 200
    json_response = response.json()
    assert json_response['agent_id'] == agent.id