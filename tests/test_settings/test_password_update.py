import pytest
from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession


from property_street_backend.tests.auth.test_user_creation import (
    user_data,
    create_test_user,
)
from property_street_backend.app.controllers.actors.models import User
from property_street_backend.app.controllers.auth.services import fetch_access_token
from property_street_backend.app.controllers.settings.routes import password_update_set_token


@pytest.mark.asyncio
async def test_password_update(client__fixture):
    # Extract the fixture object
    fixture_obj: dict = client__fixture
    test_db: AsyncSession = fixture_obj["db"]
    httpx_client: AsyncClient = fixture_obj["http_client"]
    redis_client: Redis = fixture_obj["redis_client"]

    created_user: User = await create_test_user(test_db)
    
    # Generate an access token for authentication
    token_obj = fetch_access_token(user=created_user)
    token = token_obj['access_token']
    headers = {"Authorization": f"Bearer {token}"}

    # Make a request to authenticate user
    response = await httpx_client.post(
        "/settings/confirm-password-for-update", 
        json = {"password": user_data.password},
        headers=headers,
    )
    assert response.status_code == 200

    # check redis token
    email = created_user.email
    password_update_token = password_update_set_token(email)
    assert await redis_client.exists(password_update_token), "Token for password update not cached."

    # Make a request to update password
    new_password = "whatchamacallu"
    response = await httpx_client.post(
        "/settings/update-password", 
        json = {"password": new_password},
        headers=headers,
    )
    assert response.status_code == 200

    password_update_token = password_update_set_token(email)
    assert not await redis_client.exists(password_update_token), "Token failed to be removed."


    # Trying making a request to update password
    response = await httpx_client.post(
        "/settings/update-password", 
        json = {"password": new_password},
        headers=headers,
    )
    assert response.status_code == 400