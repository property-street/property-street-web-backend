import pytest

from property_street_backend.app.models import UserSetting
from property_street_backend.app.controllers.auth import (
    fetched_access_token,
    create_user,
    verify_password,
)
from property_street_backend.app.schemas.auth_schemas import UserRegistrationSchema


@pytest.mark.asyncio
async def test_password_update(client__fixture):
    # Extract the fixture object
    fixture_obj = await client__fixture.__anext__()
    test_db = fixture_obj.get("db")
    client = fixture_obj.get("http_client")

    # Define a test user and create it
    user_data = UserRegistrationSchema(
        email="test@example.com",
        username="testuser",
        password="password123"
    )
    created_user = await create_user(test_db, user_data)

    # Generate an access token for authentication
    token_obj = fetched_access_token(user=created_user)
    token = token_obj['access_token']
    headers = {"Authorization": f"Bearer {token}"}

    # ✅ Test valid password update
    update_obj = {'password': 'newpassword'}
    response = await client.post(
        "/settings/update-password",
        json=update_obj,
        headers=headers,
    )
    assert response.status_code == 200

    # Refresh user instance and verify the password was updated
    await test_db.refresh(created_user)
    assert verify_password(update_obj['password'], created_user.password_hash)

    # ✅ Test rejecting when new password is the same as the current one
    response = await client.post(
        "/settings/update-password",
        json=update_obj,  # Using the same 'newpassword' again
        headers=headers,
    )
    assert response.status_code == 400
    assert response.json()['detail'] == "New password cannot be the same as the current password"

    # ✅ Test rejecting requests without authentication
    response = await client.post(
        "/settings/update-password",
        json=update_obj
    )
    assert response.status_code == 401  # Unauthorized

    # ✅ Test rejecting requests with missing password field
    response = await client.post(
        "/settings/update-password",
        json={},
        headers=headers,
    )
    assert response.status_code == 422  # Unprocessable Entity (Missing required field)
