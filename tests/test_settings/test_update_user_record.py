import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import User
from property_street_backend.tests.auth.test_user_creation import create_test_user
from property_street_backend.app.schemas.auth_schemas import UserRegistrationSchema
from property_street_backend.app.controllers.auth.services import fetch_access_token
from property_street_backend.app.controllers.settings.services import user_record_update
from property_street_backend.tests.activity.test_controller.test_objects import area_template
from property_street_backend.app.controllers.settings.schemas import UserSettingResponseSchema

@pytest.mark.asyncio
async def test_user_record_update(
    client__fixture
):
    # get the yield client objects
    async for fixture_obj in client__fixture:
        # extract the database entry
        httpx_client: AsyncClient = fixture_obj["http_client"]
        test_db: AsyncSession = fixture_obj["db"]
        break
    
    settings_data_template = {
        "phone_number": "123456789",
        "email_notification": False,
        "push_notification": False,
        "dial_code": "+234",
    }
    user_data_template = {
        "email": "new_user@gmail.com",
    }

    update_obj = {
        0: {
            # user_settings
            "db_table_id": -1,
            "db_delete": False,
            "db_table_name": "UserSetting",

            # fields
            "fields": {
                **settings_data_template,
            }
        },
        1: {
            # user
            "db_table_id": -1,
            "db_delete": False,
            "db_table_name": "User",

            # fields
            "fields": {
                **user_data_template,
                "relationship":{
                    "settings": 0
                }
            }
        },
        2: {
            # area
            "db_table_id": -1,
            "db_delete": False,
            "db_table_name": "Area",

            # fields
            "fields": {
                **area_template,

                "relationship":{
                    "occupant": 0,
                }
            }
        }
    }

    # Call the create_user function
    created_user: User = await create_test_user(test_db)
    # Generate an access token for authentication
    token_obj = fetch_access_token(user=created_user)
    token = token_obj['access_token']
    headers = {"Authorization": f"Bearer {token}"}

    #**# Make updates on both object
    # call the update_user_record function
    response = await httpx_client.post(
        '/settings/update-user-and-settings',
        headers = headers,
        json = update_obj
    )
    await test_db.refresh(created_user)
    user_record = response.json()
    # user assertions
    assert user_record['user']['email'] == user_data_template['email']
    assert user_record['user']['email'] == created_user.email
    
    # settings assertions
    assert user_record['phone_number'] == settings_data_template['phone_number']
    assert user_record['email_notification'] == settings_data_template['email_notification']
    assert user_record['push_notification'] == settings_data_template['push_notification']
    assert user_record['dial_code'] == settings_data_template['dial_code']


    assert user_record['area']['country'] == area_template['country']
    assert user_record['area']['state_or_province'] == area_template['state_or_province']
    assert user_record['area']['city_or_town'] == area_template['city_or_town']
    assert user_record['area']['street'] == area_template['street']


    #**# Send an independent non-existent settings object
    # delete the previous instance since the relationship is 1-1
    # commit to the database and refresh the user instance
    # update the update_obj
    #await test_db.delete(user_settings)
    #await test_db.commit()
    #await test_db.refresh(created_user)
    #
    #update_obj[1] =  {
    #    # tag 1
    #    "db_table_id": -1,
    #    "db_delete": False,
    #    "db_table_name": "UserSetting",
#
    #    # fields
    #    "fields": {
    #        "phone_number": "country_code-phone-digits",
    #        "country": "Algeria",
    #        "push_notification": True,
#
    #        "relationship":{
    #            "user" : 0
    #        }
    #    }
    #}
    ## call the update function
    #await user_record_update(
    #    data_to_be_processed = update_obj,
    #    db = test_db
    #)
    ## settings assertions
    ## ensure the user instance reflects the current change from the database
    #await test_db.refresh(created_user)
    #user_settings = created_user.user_settings
    #settings_data_template = update_obj[1]['fields']
    #assert user_settings.phone_number == settings_data_template['phone_number']
    #assert user_settings.country == settings_data_template['country']
    #assert user_settings.push_notification == settings_data_template['push_notification']
#
#
#
    ##**# Send an independent existent settings object
    #settings_id = user_settings.id
    #update_obj = {
    #    0: {
    #        "db_table_id": settings_id,
    #        "db_delete": False,
    #        "db_table_name": "UserSetting",
    #        
    #        "fields":{
    #            "phone_number": "+123-199820101",
    #            "country": "Parkistan",
    #            "push_notification": False,
    #        }
    #    }
    #}
    ## call the update function
    #await user_record_update(
    #    data_to_be_processed = update_obj,
    #    db = test_db
    #)
    ## settings assertions
    ## ensure the user instance reflects the current change from the database
    #await test_db.refresh(user_settings)
    #settings_data_template =  update_obj[0]['fields']
    #assert user_settings.phone_number == settings_data_template['phone_number']
    #assert user_settings.country == settings_data_template['country']
    #assert user_settings.push_notification == settings_data_template['push_notification']
