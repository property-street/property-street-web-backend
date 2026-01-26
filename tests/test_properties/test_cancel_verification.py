import pytest
from httpx import AsyncClient
from redis.asyncio import Redis
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from .test_processing import property_payload
from property_street_backend.app.models import Asset
from .test_processing.test_apply_model import create_test_asset
from property_street_backend.app.controllers.auth.utils import ensure_admin_user
from property_street_backend.app.controllers.auth.services import fetch_access_token
from property_street_backend.tests.auth.test_create_agent import create_test_agent, UserRegistrationSchema
from .test_processing.test_newly_created_asset_cache_management import assertions_after_newly_created_cache_removal


@pytest.mark.asyncio
async def test_cancel_verification_endpoint(client__fixture):
    # fetch fixtures
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
    # Mark it verified
    property.verified = True
    await test_db.commit()
    await test_db.refresh(property)

    assert property.verified is True

    # get admin token
    admin = await ensure_admin_user(test_db)
    token_obj = fetch_access_token(user=admin)
    admin_token = token_obj['access_token']
    headers = {"Authorization": f"Bearer {admin_token}"}

    # call cancel verification endpoint
    resp = await httpx_client.post(f"/assets/cancel-verification/{property.id}/", headers=headers)
    assert resp.status_code == 200
    resp_json = resp.json()

    # response should show verified False and datetime_declined set
    assert resp_json.get('verified') is False
    assert resp_json.get('datetime_declined') is not None

    # verify directly in DB
    updated: Asset = await test_db.get(Asset, property.id)
    assert updated.verified is False
    assert updated.datetime_declined is not None

    # datetime_declined should be recent (within 60s)
    dt = updated.datetime_declined
    assert (datetime.now(timezone.utc) - dt).total_seconds() < 60
    await assertions_after_newly_created_cache_removal(
        redis_client, property.id
    )