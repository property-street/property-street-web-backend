import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from property_street_backend.tests.auth.test_signin import signin_user
from property_street_backend.tests.auth import create_test_user, user_data
from property_street_backend.app.controllers.auth.models import RefreshSession


@pytest.mark.asyncio
async def test_signin_creates_refresh_session_and_refreshes_access_token(client__fixture):
    client: AsyncClient = client__fixture["http_client"]
    db: AsyncSession = client__fixture["db"]

    user, token_payload = await signin_user(client, db)

    refresh_session = (
        await db.execute(
            select(RefreshSession).where(
                RefreshSession.id == token_payload["refresh_session_id"],
                RefreshSession.user_id == user.id,
            )
        )
    ).scalars().first()
    assert refresh_session is not None
    assert refresh_session.is_revoked is False
    assert refresh_session.token_hash != token_payload["refresh_token"]

    response = await client.post(
        f"/auth/refresh/{token_payload['refresh_session_id']}/",
        json=token_payload["refresh_token"],
    )
    assert response.status_code == 200
    refreshed_payload = response.json()
    assert refreshed_payload["access_token"]
    assert refreshed_payload["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_token_management_lists_and_revokes_refresh_session(client__fixture):
    client: AsyncClient = client__fixture["http_client"]
    db: AsyncSession = client__fixture["db"]

    _, token_payload = await signin_user(client, db)
    headers = {"Authorization": f"Bearer {token_payload['access_token']}"}

    response = await client.get("/token-management/sessions", headers=headers)
    assert response.status_code == 200
    sessions = response.json()
    assert any(item["id"] == token_payload["refresh_session_id"] for item in sessions)

    response = await client.post(
        f"/token-management/revoke/refresh/{token_payload['refresh_session_id']}",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["detail"] == "Refresh token revoked"

    refresh_session = await db.get(RefreshSession, token_payload["refresh_session_id"])
    assert refresh_session.is_revoked is True


@pytest.mark.asyncio
async def test_token_management_revoke_all_sessions(client__fixture):
    client: AsyncClient = client__fixture["http_client"]
    db: AsyncSession = client__fixture["db"]

    user, token_payload = await signin_user(client, db)
    headers = {"Authorization": f"Bearer {token_payload['access_token']}"}

    response = await client.post("/token-management/revoke/all", headers=headers)
    assert response.status_code == 200

    result = await db.execute(
        select(RefreshSession).where(RefreshSession.user_id == user.id)
    )
    assert all(session.is_revoked for session in result.scalars().all())
