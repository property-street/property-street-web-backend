import pytest
from datetime import datetime, timezone

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import Asset
from property_street_backend.tests.test_properties.test_create_asset import create_test_asset
from property_street_backend.app.controllers.auth.utils import ensure_admin_user
from property_street_backend.app.controllers.auth.services import fetch_access_token


@pytest.mark.asyncio
async def test_cancel_verification_endpoint(client__fixture):
    # fetch fixtures
    httpx_client: AsyncClient = client__fixture['http_client']
    test_db: AsyncSession = client__fixture['db']

    # create an asset and mark it verified
    created_asset: Asset = await create_test_asset(test_db)
    created_asset.verified = True
    await test_db.commit()
    await test_db.refresh(created_asset)

    assert created_asset.verified is True

    # get admin token
    admin = await ensure_admin_user()
    token_obj = fetch_access_token(user=admin)
    admin_token = token_obj['access_token']
    headers = {"Authorization": f"Bearer {admin_token}"}

    # call cancel verification endpoint
    resp = await httpx_client.post(f"/assets/cancel-verification/{created_asset.id}/", headers=headers)
    assert resp.status_code == 200
    resp_json = resp.json()

    # response should show verified False and datetime_declined set
    assert resp_json.get('verified') is False
    assert resp_json.get('datetime_declined') is not None

    # verify directly in DB
    updated: Asset = await test_db.get(Asset, created_asset.id)
    assert updated.verified is False
    assert updated.datetime_declined is not None

    # datetime_declined should be recent (within 60s)
    dt = updated.datetime_declined
    assert (datetime.now(timezone.utc) - dt).total_seconds() < 60
