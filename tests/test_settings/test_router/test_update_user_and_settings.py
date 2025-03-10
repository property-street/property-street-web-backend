import pytest

from property_street_backend.app.models import UserSetting
from property_street_backend.app.controllers.auth import (
    fetched_access_token,
)
from property_street_backend.app.controllers.auth import (
    create_user, 
    verify_password,
)
from property_street_backend.app.schemas.auth_schemas import UserRegistrationSchema
from property_street_backend.app.schemas.settings_schemas import UserSettingSchema


@pytest.mark.asyncio
async def test_user_record_update(client__fixture):
    # Extract the fixture object
    fixture_obj = await client__fixture.__anext__()
    test_db = fixture_obj.get("db")
    client = fixture_obj.get("http_client")

    update_obj = {
        0: {
            # tag 1
            "db_table_id": -1,
            "db_delete": False,
            "db_table_name": "User",

            # fields
            "fields": {
                "email": "new_user@gmail.com",
                "password": "password_hash",
            }
        },
        1: {
            # tag 1
            "db_table_id": -1,
            "db_delete": False,
            "db_table_name": "UserSetting",

            # fields
            "fields": {
                "phone_number": "country_code-phone-digits",
                "address": "4 unity close Ada george", 
                "country": "Nigeria",
                "email_notification": False,
                "push_notification": False,

                "relationship":{
                    "user": 0,
                }
            }
        }
    }

    # Define a test user and create it
    user_data = UserRegistrationSchema(
        email="test@example.com",
        username="testuser",
        password="password123"
    )
    created_user = await create_user(test_db, user_data)
    user_id = created_user.id
    update_obj[0]['db_table_id'] = user_id

    # Generate an access token for authentication
    token_obj = fetched_access_token(user=created_user)
    token = token_obj['access_token']
    headers = {"Authorization": f"Bearer {token}"}

    # Make a request when no setting instance hasn't been associated with the user
    # assert that the user has no settings
    response = await client.post(
        "/settings/update-user-and-settings", 
        json = update_obj,
        headers=headers,
    )
    assert response.status_code == 200

    # refresh user instance and 
    # assert to verify the updated data
    await test_db.refresh(created_user) 
    fields = update_obj[0]['fields']
    assert created_user.email == fields['email']
    assert verify_password(fields['password'],created_user.password_hash)
    
    # settings assertions
    user_settings = created_user.user_settings
    fields = update_obj[1]['fields']
    assert user_settings.phone_number == fields['phone_number']
    assert user_settings.address == fields['address']
    assert user_settings.country == fields['country']
    assert user_settings.email_notification == fields['email_notification']
    assert user_settings.push_notification == fields['push_notification']