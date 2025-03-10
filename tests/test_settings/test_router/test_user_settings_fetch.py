import pytest

from property_street_backend.app.models import UserSetting
from property_street_backend.app.controllers.auth import (
    fetched_access_token,
)
from property_street_backend.app.controllers.auth import create_user
from property_street_backend.app.schemas.auth_schemas import UserRegistrationSchema
from property_street_backend.app.schemas.settings_schemas import UserSettingSchema


@pytest.mark.asyncio
async def test_user_record_update(client__fixture):
    # Extract the fixture object
    async for fixture_obj in client__fixture:
        test_db = fixture_obj.get("db")
        client = fixture_obj.get("http_client")
        break  # Stop iteration after first fixture retrieval

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

    # Make a request when no setting instance hasn't been associated with the user
    # assert that the user has no settings
    response = await client.get("/settings", headers=headers)
    assert response.status_code == 200
    json_response = response.json()
    assert not json_response.get('has_settings')
    

    # Define and create a setting instance for the user
    setting_data = UserSettingSchema(
        phone_number="country_code-phone-digits",
        address="4 unity close Ada george", 
        country="Nigeria",
        email_notification=False,
        push_notification=False,
    )
    user_setting = UserSetting(
        **(vars(setting_data))  # Convert to dictionary before unpacking
    )
    user_setting.user = created_user  # Explicitly set the user
    test_db.add(user_setting)
    await test_db.commit()

    # Make the request
    # Assertions
    response = await client.get("/settings", headers=headers)
    assert response.status_code == 200
    json_response = response.json()
    settings_details = json_response.get('settings_data')
    assert settings_details.get('phone_number') == setting_data.phone_number
    assert settings_details.get('address') == setting_data.address
    assert settings_details.get('country') == setting_data.country
    assert settings_details.get('email_notification') is False
    assert settings_details.get('push_notification') is False
