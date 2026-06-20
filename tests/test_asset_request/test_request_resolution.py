import pytest
from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import (
    User,
    Asset, 
    AssetRequest,
)
from tests.auth.test_create_agent import create_test_agent
from property_street_backend.app.controllers.auth.services import fetch_access_token
from property_street_backend.tests.test_properties.test_processing import property_payload
from property_street_backend.app.controllers.assets.property_processor_utils import property_create_persistence_ttl
from property_street_backend.tests.test_asset_request import payload as property_request_payload



@pytest.mark.asyncio
async def test_resolve_request(client__fixture: dict):
    test_db: AsyncSession = client__fixture["db"]
    http_client: AsyncClient = client__fixture["http_client"]

    agent = await create_test_agent(test_db)
    token = fetch_access_token(user=agent)['access_token']
    headers = {"Authorization": f"Bearer {token}"}

    #=============================
    # Make property request
    #=============================
    response = await http_client.post(
        "/asset-requests",
        json=property_request_payload,
        headers=headers 
    )
    assert response.status_code == 201
    request_id = response.json()['id']
    assert request_id

    #==========================================
    # request resolution
    #==========================================
    payload = property_payload(agent.id)
    response = await http_client.post(
        f"/asset-requests/resolve/{request_id}/",
        json={"property": payload},
        headers=headers,
    )
    assert response.status_code == 200
    updated_request = response.json()
    resolutions = updated_request['resolutions']
    assert resolutions
    assert len(resolutions) == 1