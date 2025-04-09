import pytest
from sqlalchemy.future import select


from property_street_backend.app.controllers.auth import create_user
from property_street_backend.app.schemas.auth_schemas import UserRegistrationSchema
from property_street_backend.app.controllers.activity.user_update import user_record_update


@pytest.mark.asyncio
async def test_user_record_update(
    client__fixture
):
    # get the yield client objects
    async for fixture_obj in client__fixture:
        break
    
    # extract the database entry
    test_db = fixture_obj.get("db")

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

    # Define a test user
    user_data = UserRegistrationSchema(
        email="test@example.com",
        username="testuser",
        password="password123"
    )
    
    # Call the create_user function
    created_user = await create_user(test_db, user_data)
    user_id = created_user.id

    # User creation assertions
    assert created_user is not None
    assert created_user.email == user_data.email
    assert created_user.username == user_data.username
    assert created_user.password_hash != user_data.password  # Ensure the password is hashed

    # assign the id of the created user to the first
    # db_table_id of the first update object
    update_obj[0]['db_table_id'] = user_id

    #**# Make updates on both object
    # call the update_user_record function
    await user_record_update(
        data_to_be_processed = update_obj,
        db = test_db
    )

    # refresh the user instance and 
    # assert to verify the updated data
    await test_db.refresh(created_user) 
    fields = update_obj[0]['fields']
    assert created_user.email == fields['email']
    assert created_user.password_hash == fields['password_hash']  # Ensure the password is hashed
    
    # settings assertions
    user_settings = created_user.user_settings
    fields = update_obj[1]['fields']
    assert user_settings.phone_number == fields['phone_number']
    assert user_settings.address == fields['address']
    assert user_settings.country == fields['country']
    assert user_settings.email_notification == fields['email_notification']
    assert user_settings.push_notification == fields['push_notification']



    #**# Send an independent non-existent settings object
    # delete the previous instance since the relationship is 1-1
    # commit to the database and refresh the user instance
    # update the update_obj
    await test_db.delete(user_settings)
    await test_db.commit()
    await test_db.refresh(created_user)
    
    update_obj[1] =  {
        # tag 1
        "db_table_id": -1,
        "db_delete": False,
        "db_table_name": "UserSetting",

        # fields
        "fields": {
            "phone_number": "country_code-phone-digits",
            "country": "Algeria",
            "push_notification": True,

            "relationship":{
                "user" : 0
            }
        }
    }
    # call the update function
    await user_record_update(
        data_to_be_processed = update_obj,
        db = test_db
    )
    # settings assertions
    # ensure the user instance reflects the current change from the database
    await test_db.refresh(created_user)
    user_settings = created_user.user_settings
    fields = update_obj[1]['fields']
    assert user_settings.phone_number == fields['phone_number']
    assert user_settings.country == fields['country']
    assert user_settings.push_notification == fields['push_notification']



    #**# Send an independent existent settings object
    settings_id = user_settings.id
    update_obj = {
        0: {
            "db_table_id": settings_id,
            "db_delete": False,
            "db_table_name": "UserSetting",
            
            "fields":{
                "phone_number": "+123-199820101",
                "country": "Parkistan",
                "push_notification": False,
            }
        }
    }
    # call the update function
    await user_record_update(
        data_to_be_processed = update_obj,
        db = test_db
    )
    # settings assertions
    # ensure the user instance reflects the current change from the database
    await test_db.refresh(user_settings)
    fields =  update_obj[0]['fields']
    assert user_settings.phone_number == fields['phone_number']
    assert user_settings.country == fields['country']
    assert user_settings.push_notification == fields['push_notification']
