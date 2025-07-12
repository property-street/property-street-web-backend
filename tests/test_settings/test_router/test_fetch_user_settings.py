import pytest
from datetime import date
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import UserSetting
from property_street_backend.app.controllers.auth import (
    fetched_access_token,
)
from property_street_backend.app.models import Area
from property_street_backend.app.schemas.area_schema import AreaSchema
from property_street_backend.tests.auth.test_user_creation import create_test_user
from property_street_backend.app.controllers.settings.schemas import UserSettingSchema
from property_street_backend.tests.activity.test_controller.test_objects import area_template


@pytest.mark.asyncio
async def test_user_record_update(client__fixture):
    # Extract the fixture object
    async for fixture_obj in client__fixture:
        test_db: AsyncSession = fixture_obj["db"]
        client: AsyncClient = fixture_obj["http_client"]
        break  # Stop iteration after first fixture retrieval

    # Create a test user
    created_user = await create_test_user(test_db)
    
    # Generate an access token for authentication
    token_obj = fetched_access_token(user=created_user)
    token = token_obj['access_token']
    headers = {"Authorization": f"Bearer {token}"}

    # Make a request when no setting instance hasn't been associated with the user
    # refresh the user
    # make assertions
    response = await client.get("/settings", headers=headers)
    assert response.status_code == 200
    json_response: dict = response.json()
    await test_db.refresh(created_user)
    assert json_response.get('email') == created_user.email
    assert json_response.get('first_name') == created_user.first_name
    assert json_response.get('last_name') == created_user.last_name
    assert not json_response.get('has_settings')
    

    area_data = {
        **area_template,
        'zip_or_postal_code' : '854BEC',
        'building_name_or_suite': 'Jacobe suite'
    }
    setting_data = UserSetting(
        phone_number="+234 9031145687",
        email_notification=False,
        push_notification=True,
        date_of_birth = date(1990, 1, 1),  # Use date object and convert to ISO format
        areas = [Area(**area_data),],
        user = created_user  
    )
    test_db.add(setting_data)
    await test_db.commit()

    # Make the request
    # Assertions
    response = await client.get("/settings", headers=headers)
    assert response.status_code == 200
    json_response = response.json()
    assert json_response.get('has_settings')
    assert json_response.get('phone_number') == setting_data.phone_number
    assert date.fromisoformat(json_response.get('date_of_birth')) == setting_data.date_of_birth
    assert json_response.get('email_notification') == setting_data.email_notification
    assert json_response.get('push_notification') == setting_data.push_notification
    assert AreaSchema.model_validate(json_response.get('areas')[0])
