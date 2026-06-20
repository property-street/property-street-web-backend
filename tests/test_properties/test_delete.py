import pytest
from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from .test_processing import property_payload
from property_street_backend.app.models import (
    User,
    Asset, 
)
from tests.auth.test_create_agent import create_test_agent
from property_street_backend.app.controllers.auth.services import fetch_access_token
from property_street_backend.app.controllers.assets.property_processor_utils import property_create_persistence_ttl
from property_street_backend.tests.activity.test_controller.test_newly_created_asset_cache_management import (
    assertions_after_caching,
)


@pytest.mark.asyncio
async def test_delete(client__fixture: dict):
    test_db: AsyncSession = client__fixture["db"]
    redis_client: Redis = client__fixture["redis_client"]
    http_client: AsyncClient = client__fixture["http_client"]

    agent = await create_test_agent(test_db)
    token = fetch_access_token(user=agent)['access_token']
    headers = {"Authorization": f"Bearer {token}"}

    #==========================
    # Featured request
    #==========================
    payload = property_payload(agent.id)
    response = await http_client.post(
        "/assets/create-property",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 201
    property = response.json()
    id = property.get('id',None)
    assert id
    # cache assertions
    # await assertions_after_caching(
    #     redis_client=redis_client,
    #     asset_id=property["id"],
    #     asset_data=property,
    #     expiry_seconds = property_create_persistence_ttl()
    # )
    property = await test_db.get(Asset, id)
    assert property
    response = await http_client.delete(
        f'/assets/delete/{id}/',
        headers = headers
    )
    assert response.status_code == 204
    assert not await test_db.get(Asset, id)