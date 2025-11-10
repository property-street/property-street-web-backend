import pytest

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import Asset
from property_street_backend.tests.test_properties.test_create_asset import create_test_asset
from property_street_backend.app.controllers.auth.utils import ensure_admin_user
from property_street_backend.app.controllers.auth.services import fetch_access_token


@pytest.mark.asyncio
async def test_confirm_verification_endpoint(client__fixture):
    # get fixtures
    httpx_client: AsyncClient = client__fixture['http_client']
    test_db: AsyncSession = client__fixture['db']

    # create an unverified asset
    created_asset: Asset = await create_test_asset(test_db)
    # ensure it's not verified initially
    assert not created_asset.verified

    # ensure admin exists and get token
    admin = await ensure_admin_user()
    token_obj = fetch_access_token(user=admin)
    admin_token = token_obj['access_token']
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
