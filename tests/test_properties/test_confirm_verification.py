import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import Asset
from .test_processing.test_create_with_apply_model import create_test_asset
from property_street_backend.app.controllers.auth.utils import ensure_admin_user
from property_street_backend.app.controllers.auth.services import fetch_access_token
from property_street_backend.tests.auth.test_create_agent import create_test_agent, UserRegistrationSchema


@pytest.mark.asyncio
async def test_confirm_verification_endpoint(client__fixture):
    # get fixtures
    httpx_client: AsyncClient = client__fixture['http_client']
    test_db: AsyncSession = client__fixture['db']

    agent = await create_test_agent(test_db,UserRegistrationSchema(
        email="crankgig@gmail.com",
        username="testuser",
        password="password123",
        first_name="John",
        last_name="Doe",
    ))
    # create an unverified asset
    created_asset: Asset = await create_test_asset(test_db, agent.id)
    # ensure it's not verified initially
    assert not created_asset.verified

    # ensure admin exists and get token
    admin = await ensure_admin_user()
    admin_token = fetch_access_token(user=admin)['access_token']
    headers = {"Authorization": f"Bearer {admin_token}"}

    # call the confirm verification endpoint
    resp = await httpx_client.post(f"/assets/confirm-verification/{created_asset.id}/", headers=headers)
    assert resp.status_code == 200

    resp_json = resp.json()
    # response should indicate verified True (AssetResponseSchema serialization)
    assert resp_json.get('verified') is True

    # verify directly in DB
    updated: Asset = await test_db.get(Asset, created_asset.id)
    assert updated.verified is True
