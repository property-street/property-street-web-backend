import pytest
from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import EmailStr

from property_street_backend.tests.auth.test_user_creation import create_test_user
from property_street_backend.app.controllers.auth.services import authenticate_user
from property_street_backend.app.controllers.auth.services import (
    sec_field_name,
    hset_password_reset_key,
)

@pytest.mark.asyncio
async def test_send_password_reset_mail(client__fixture):
    test_db: AsyncSession = client__fixture["db"]
    httpx_client: AsyncClient = client__fixture["http_client"]
    redis_client: Redis = client__fixture["redis_client"]

    # Create user
    test_user = await create_test_user(test_db)
    email = "crankgig@gmail.com"
    test_user.email = email
    test_db.add(test_user)
    await test_db.commit()

    #-- Send password reset mail --#
    response = await httpx_client.post(
        "/auth/send-password-reset-mail",
        json={"email": email},
    )
    assert response.status_code == 200
    data = response.json()
    print(data)
    assert "detail" in data
    assert "expiry" in data

    hset_key = hset_password_reset_key(email)
    assert redis_client.exists(hset_key)

    secret = redis_client.hget(hset_key, sec_field_name)
    token=f'{test_user.id}_{secret}'

    #-- check validity of the token --#
    response = await httpx_client.get(
        f"/auth/check-email-reset-validity?token={token}",
    )
    assert response.status_code == 200


    #-- change password --#
    new_password = "new_secure_password123"
    token = "valid_token_for_user"

    response = await httpx_client.post(
        "/auth/change-password",
        json={"token": token, "password": new_password},
    )
    assert response.status_code == 200
    await authenticate_user(test_db, email, new_password)
    assert not await redis_client.exists(user_key)