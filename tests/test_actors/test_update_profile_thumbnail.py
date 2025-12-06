import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.tests.auth import create_test_user
from property_street_backend.app.controllers.auth.services import fetch_access_token
from property_street_backend.tests.activity.test_controller.test_objects import cloud_image_template


@pytest.mark.asyncio
async def test_profile_thumbnail_update(client__fixture):
    test_db: AsyncSession = client__fixture["db"]
    httpx_client: AsyncClient = client__fixture["http_client"]

    created_user = await create_test_user(test_db)

    payload = {
        **cloud_image_template
    }

    # Generate an access token for authentication
    token = fetch_access_token(user=created_user)['access_token']
    headers = {"Authorization": f"Bearer {token}"}

    # Make a request when no setting instance hasn't been associated with the user
    # assert that the user has no settings
    response = await httpx_client.patch(
        "/actors/update-profile-avatar/", 
        json = payload,
        headers=headers,
    )
    assert response.status_code == 200
    avatar = response.json()
    assert "id" in avatar
    assert "public_id" in avatar
    assert "secure_url" in avatar