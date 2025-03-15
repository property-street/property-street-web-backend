import pytest

from property_street_backend.app.controllers.auth import (
    fetched_access_token,
)
from property_street_backend.app.controllers.auth import (
    create_user, 
)
from property_street_backend.app.schemas.auth_schemas import UserRegistrationSchema


@pytest.mark.asyncio
async def test_user_profile_thumbnail_update(client__fixture):
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
    user_id = created_user.id
    update_obj = {
        0: {
            # image for asset feature
            "db_delete": False,
            "db_table_id": -1,
            "db_table_name": "CloudImageDetail",

            # fields
            "fields": {
                "cloud_asset_id":"dkajdlkajdlkajsdkfjasldkfj",
                "format": "jpg",
                "bytes": 102400,
                "height": 800,
                "public_id": "test_image_123",
                "secure_url": "https://example.com/test_image.jpg",
                "width": 600,
            }
        },
        1: {
            # tag 1
            "db_table_id": user_id,
            "db_delete": False,
            "db_table_name": "User",

            # fields
            "fields": {
                "relationship":{
                    "profile_avatar": 0,
                }
            }
        }
    }

    # Generate an access token for authentication
    token_obj = fetched_access_token(user=created_user)
    token = token_obj['access_token']
    headers = {"Authorization": f"Bearer {token}"}

    # Make a request when no setting instance hasn't been associated with the user
    # assert that the user has no settings
    response = await client.post(
        "/activity/update-profile-thumbnail", 
        json = update_obj,
        headers=headers,
    )
    assert response.status_code == 200

    # refresh user instance and 
    # assert to verify the updated data
    await test_db.refresh(created_user) 
    cover_image = created_user.profile_avatar
    fields = update_obj[0]['fields']
    assert cover_image.format == fields['format']
    assert cover_image.bytes == fields['bytes']
    assert cover_image.height == fields['height']
    assert cover_image.public_id == fields['public_id']
    assert cover_image.secure_url == fields['secure_url']
    assert cover_image.width == fields['width']