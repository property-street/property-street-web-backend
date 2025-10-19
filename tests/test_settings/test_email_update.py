import pytest
from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import UserSetting
from property_street_backend.app.controllers.auth.services import (
    fetch_access_token,
)
from property_street_backend.app.models import Area
from property_street_backend.app.schemas.area_schema import AreaResponseSchema
from property_street_backend.tests.auth.test_user_creation import create_test_user, user_data
from property_street_backend.tests.activity.test_controller.test_objects import area_template


@pytest.mark.asyncio
async def test_email_update(client__fixture):
    test_db: AsyncSession = client__fixture["db"]
    httpx_client: AsyncClient = client__fixture["http_client"]
    redis_client: Redis = client__fixture["redis_client"]

    # Create a test user
    created_user = await create_test_user(test_db)
    
    # Generate an access token for authentication
    token_obj = fetch_access_token(user=created_user)
    token = token_obj['access_token']
    headers = {"Authorization": f"Bearer {token}"}

    response = await httpx_client.post(
        "/settings/email-update-validation", 
        json={"email": created_user.email},
        headers=headers
    )
    assert response.status_code == 400

    new_email="whoopydydo@gmail.com"
    response = await httpx_client.post(
        "/settings/email-update-validation", 
        json={"email": new_email},
        headers=headers
    )
    assert response.status_code == 200

    
    # Define the post data for sending the email verification code
    send_code_data = {
        "email": new_email,
        "username": "whoopdy",
    }

    # Request a verification code
    response = await httpx_client.post(
        "/auth/send-email-verification-code",
        json=send_code_data  # Use json instead of data for a JSON body
    )
    # Assertions for sending the verification code
    assert response.status_code == 200
    json_response: dict = response.json()
    assert json_response.get("message") == "A new verification code has been sent to your email."
    reason = "email_verification"
    user_key = f'{new_email}:{reason}'
    cached_code = await redis_client.hget(user_key, reason)
    emailed_code = (
        cached_code.decode() 
        if isinstance(cached_code,bytes) 
        else cached_code
    )
    assert emailed_code, "Email verification code not persisted."


    # confirm verification code and update password
    response = await httpx_client.post(
        "/settings/confirm-email-update",
        json={"email": new_email, 
              "code": emailed_code},
        headers=headers
    )
    assert response.status_code == 200
    await test_db.refresh(created_user)
    assert created_user.email == new_email, "Email update failed."