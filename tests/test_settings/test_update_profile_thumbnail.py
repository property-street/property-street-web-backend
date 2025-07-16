import pytest

from property_street_backend.tests.auth.test_user_creation import create_test_user
from property_street_backend.app.controllers.auth.services import fetch_access_token
from property_street_backend.app.controllers.settings.schemas import UserSettingResponseSchema


@pytest.mark.asyncio
async def test_user_profile_thumbnail_update(client__fixture):
    
    # Extract the fixture object
    async for fixture_obj in client__fixture:
        test_db = fixture_obj["db"]
        httpx_client = fixture_obj["http_client"]
        break

    created_user = await create_test_user(test_db)
    update_obj = {
        0: {
            # image for asset feature
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
            "db_table_id": -1,
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
    token_obj = fetch_access_token(user=created_user)
    token = token_obj['access_token']
    headers = {"Authorization": f"Bearer {token}"}

    # Make a request when no setting instance hasn't been associated with the user
    # assert that the user has no settings
    response = await httpx_client.post(
        "/settings/update-user-and-settings", 
        json = update_obj,
        headers=headers,
    )
    assert response.status_code == 200
    json_response = response.json()


    recent_settings = UserSettingResponseSchema.model_validate(json_response) 
    recent_settings.user.profile_avatar_url == update_obj[0]['fields']['secure_url']