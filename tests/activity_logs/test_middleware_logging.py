import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from property_street_backend.tests.auth.test_signin import signin_user
from property_street_backend.tests.auth import create_test_user, user_data
from property_street_backend.app.controllers.activity_logging.models import ActivityLog


@pytest.mark.asyncio
async def test_middleware_logs_authenticated_request(client__fixture):
    client: AsyncClient = client__fixture["http_client"]
    db: AsyncSession = client__fixture["db"]

    _, token_payload = await signin_user(client, db)
    headers = {"Authorization": f"Bearer {token_payload['access_token']}"}

    response = await client.get("/auth/retrieve-client-details", headers=headers)
    assert response.status_code == 200

    response = await client.get("/activity-logs/my-activities/", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any("/auth/retrieve-client-details" in item["action"] for item in data["items"])


@pytest.mark.asyncio
async def test_middleware_does_not_log_unauthenticated_requests(client__fixture):
    client: AsyncClient = client__fixture["http_client"]
    db: AsyncSession = client__fixture["db"]

    response = await client.get("/")
    assert response.status_code == 200

    result = await db.execute(select(ActivityLog))
    assert result.scalars().all() == []

    response = await client.get("/activity-logs/my-activities/")
    assert response.status_code in (401, 403)
