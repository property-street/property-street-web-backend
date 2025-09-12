import pytest
import secrets
from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.tests.auth.test_user_creation import (
    user_data,
    create_test_user,
)
from property_street_backend.app.controllers.auth.services import (
    sec_field_name,
    authenticate_user,
    hset_password_reset_key,
)

@pytest.mark.asyncio
async def test_password_change_route(client__fixture):
    test_db: AsyncSession = client__fixture["db"]
    httpx_client: AsyncClient = client__fixture["http_client"]
    redis_client: Redis = client__fixture["redis_client"]

    # Create user
    test_user = await create_test_user(test_db)
    email = test_user.email

    # Generate a new five-digit code
    secret = secrets.token_urlsafe()
    token=f'{test_user.id}_{secret}'
    user_key = hset_password_reset_key(email)
    await redis_client.hset(user_key, sec_field_name, secret)

    #-- Send a request with old password --#
    response = await httpx_client.post(
        "/auth/change-password",
        json={"token": token, "password": user_data.password},
    )
    assert response.status_code == 400
    details = response.json()
    assert details['detail'] == "New password can't be same as old."

    #-- Send a request with a new password --#
    new_password = "new_secure_password123"
    response = await httpx_client.post(
        "/auth/change-password",
        json={"token": token, "password": new_password},
    )
    assert response.status_code == 200
    await authenticate_user(test_db, email, new_password)
    assert not await redis_client.exists(user_key)