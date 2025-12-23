import pytest
from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import Asset
from property_street_backend.app.models import CloudImageDetail
from property_street_backend.tests.test_properties import create_test_asset
from property_street_backend.tests.auth.test_create_agent import create_test_agent
from property_street_backend.app.controllers.auth.services import fetch_access_token
from property_street_backend.tests.test_properties.test_processing import property_payload
from property_street_backend.app.controllers.assets.property_processor_utils import handle_property_create_update


@pytest.mark.asyncio
async def test_user_ui_metadata_retrieval(client__fixture: dict):
    # Get the yielded client object
    client: AsyncClient = client__fixture['http_client']
    test_db: AsyncSession = client__fixture['db']
    redis_client: Redis = client__fixture['redis_client']


    # Create a test agent and user
    test_agent = await create_test_agent(test_db)

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
    test_agent.profile_avatar = CloudImageDetail(**profile_avatar_details)
    test_db.add(test_agent)
    await test_db.commit()


    # Fetch a token for the user
    token = fetch_access_token(test_agent)["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/activity/user-ui-metadata", headers=headers)
    assert response.status_code == 200
    data = response.json()
    await test_db.refresh(test_agent)
    assert test_agent.id == data['id']
    assert test_agent.profile_avatar.secure_url == data.get('profile_avatar_url')
    assert data.get('is_authenticated')
    assert data['agent_details']['property_count'] == 0


    # Create a property and assert the agent's property count
    payload = property_payload(test_agent.id)
    response = await client.post(
        "/assets/create-property",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 201
    property = response.json()
    assert 'id' in property

    # Re-fetch metadata
    response = await client.get("/activity/user-ui-metadata", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data['agent_details']['property_count'] == 1


    # Fetch without authentication
    headers = {"Authorization": f"Bearer "}
    response = await client.get("/activity/user-ui-metadata", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert not all (
        data.get(i) for i in [
            'profile_avatar_url', 'first_name','user_id','is_authenticated'
        ]
    )
