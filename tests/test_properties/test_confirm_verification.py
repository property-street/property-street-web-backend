import pytest
from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from .test_processing import property_payload
from property_street_backend.app.models import Asset
from .test_processing.test_apply_model import create_test_asset
from property_street_backend.app.controllers.auth.utils import ensure_admin_user
from property_street_backend.app.controllers.auth.services import fetch_access_token
from property_street_backend.tests.auth.test_create_agent import create_test_agent, UserRegistrationSchema
from property_street_backend.app.controllers.activity.asset_routine_methods import get_property_from_newly_created_asset


@pytest.mark.asyncio
async def test_confirm_verification_endpoint(client__fixture):
    # get fixtures
    httpx_client: AsyncClient = client__fixture['http_client']
    test_db: AsyncSession = client__fixture['db']
    redis_client: Redis = client__fixture['redis_client']

    agent = await create_test_agent(test_db,UserRegistrationSchema(
        email="crankgig@gmail.com",
        username="testuser",
        password="password123",
        first_name="John",
        last_name="Doe",
    ))
    payload = property_payload(agent.id)
    agent_token = fetch_access_token(user=agent)['access_token']
    headers = {"Authorization": f"Bearer {agent_token}"}
    response = await httpx_client.post(
        "/assets/create-property",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 201
    json_resp = response.json()
    property: Asset = await test_db.get(Asset,json_resp['id'])
    property_id = property.id
    # ensure it's not verified initially
    assert not property.verified

    # ensure admin exists and get token
    admin = await ensure_admin_user(test_db)
    admin_token = fetch_access_token(user=admin)['access_token']
    headers = {"Authorization": f"Bearer {admin_token}"}

    # call the confirm verification endpoint
    resp = await httpx_client.post(f"/assets/confirm-verification/{property.id}/", headers=headers)
    assert resp.status_code == 200

    resp_json = resp.json()
    # response should indicate verified True (AssetResponseSchema serialization)
    assert resp_json.get('verified') is True

    # verify directly in DB
    updated: Asset = await test_db.get(Asset, property_id)
    assert updated.verified is True
    # verify directly in Cache
    cached_property = await get_property_from_newly_created_asset(redis_client, property_id)
    assert isinstance(cached_property, dict)
    assert cached_property.get('verified') == True