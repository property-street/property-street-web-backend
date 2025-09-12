import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.tests.auth.test_user_creation import create_test_user
from property_street_backend.app.controllers.auth.services import authenticate_user
from property_street_backend.app.controllers.auth.services import fetch_access_token
from property_street_backend.app.controllers.settings.schemas import UserSettingResponseSchema


@pytest.mark.asyncio
async def test_user_profile_thumbnail_update(client__fixture):
    
    # Extract the fixture object
    fixture_obj: dict = client__fixture
    test_db: AsyncSession = fixture_obj["db"]
    httpx_client: AsyncClient = fixture_obj["http_client"]

    created_user = await create_test_user(test_db)
    
    new_details = {
        "first_name": "McKlintok",
        "password": "whatchamacallu",
        "avatar_url": "https://example.com/test_image.jpg"
    }

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
                "secure_url": new_details['avatar_url'],
                "width": 600,
            }
        },
        1: {
            "db_table_id": -1,
            "db_table_name": "User",

            # fields
            "fields": {
                'first_name': new_details['first_name'],
                'password': new_details['password'],

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
    recent_settings.user.profile_avatar_url == new_details['avatar_url']
    recent_settings.user.first_name == new_details['first_name']
    assert await authenticate_user(test_db, created_user.email, new_details['password'])