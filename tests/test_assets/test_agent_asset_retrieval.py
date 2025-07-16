import pytest
from httpx import AsyncClient
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import Agent
from property_street_backend.tests.auth.test_create_agent import create_test_agent
from property_street_backend.app.controllers.auth.services import fetch_access_token
from property_street_backend.tests.activity.test_latest_collection import pre_commit_test_asset_collection





@pytest.mark.asyncio
async def test_agent_asset_retrieval(client__fixture):
    # Fetch the client 
    async for fixture_obj in client__fixture:
        test_db: AsyncSession = fixture_obj['db']
        httpx_client: AsyncClient = fixture_obj['http_client']
        break

    # Call the create_user function
    created_agent: Agent = await create_test_agent(test_db)

    # call the create asset and component function
    test_assets = pre_commit_test_asset_collection(created_agent.id)
    test_db.add_all(test_assets)
    await test_db.commit()

    # fetch a token for the user
    token = fetch_access_token(created_agent.user)['access_token']
    headers = {"Authorization": f"Bearer {token}"}

    size = 7
    # Make the request using the client provided by the fixture
    response = await httpx_client.get(
        f"/assets/agent-assets",
        headers = headers,
        params={"size": size}
    )
    
    # Assertions
    assert response.status_code == 200
    json_response = response.json()
    assert len(json_response) == size