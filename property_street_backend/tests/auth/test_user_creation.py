import pytest
import asyncio

from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient

from property_street_backend.app.models import User
from property_street_backend.app.controllers.auth import create_user
from property_street_backend.app.schemas.auth_schemas import UserRegistrationSchema


async def create_test_user(db):
        # Define a test user
    user_data = UserRegistrationSchema(
        email="test@example.com",
        username="testuser",
        password="password123"
    )

    return await create_user(db, user_data)

@pytest.mark.asyncio
async def test_controller_create_user(get_test_db__fixture: AsyncSession):
    try:
        # Define a test user
        user_data = UserRegistrationSchema(
            email="test@example.com",
            username="testuser",
            password="password123"
        )

        # fetch the testdb
        test_db = await get_test_db__fixture
        
        # Call the create_user function
        created_user = await create_user(test_db, user_data)

        # Assertions
        assert created_user is not None
        assert created_user.email == user_data.email
        assert created_user.username == user_data.username
        assert created_user.password_hash != user_data.password  # Ensure the password is hashed
    
        ## Verify that the user was actually created in the database
        result = await test_db.execute(
            select(User).filter(User.email == user_data.email)
        )
        user = result.scalars().first()
        assert user is not None
        assert user.username == user_data.username
    finally:
        await test_db.close()
        pass


@pytest.mark.asyncio
async def test_route_create_user(client__fixture: AsyncClient):
    # fetch the client generator
    client_gen =  client__fixture
    # get the yield client object
    client = await client_gen.__anext__()

    # Define a post data
    post_data = {
        "email": "testuser@example.com",
        "username": "testuser",
        "password": "password123",
    }

    # Make the request using the client provided by the fixture
    response = await client.post(
        "/auth/register",
        json=post_data  # Use json instead of data for a JSON body
    )

    # Assertions
    assert response.status_code == 201
    json_response = response.json()
    assert json_response.get("token_type") == "bearer"
    assert "access_token" in json_response

@pytest.mark.asyncio
async def test_route_probe_user_existence(client__fixture: AsyncClient):
    # fetch the client generator
    client_gen =  client__fixture
    # get the yield client object
    client = await client_gen.__anext__()

    # Define a post data
    post_data = {
        "email": "testuser@example.com",
        "username": "testuser",
        "password": "password123",
    }
    # sign the user up
    await client.post(
        "/auth/register",
        json=post_data  # Use json instead of data for a JSON body
    )


    # test 1
    # making a request with data that exists
    probe_data_which_exists = {
        "email": "testuser@example.com",
        "username": "testuser",
    }
    # make the request
    response = await client.post(
        "/auth/probe-user-existence",
        json=probe_data_which_exists  # Use json instead of data for a JSON body
    )
    # Assertions
    assert response.status_code == 200
    json_response = response.json()
    assert json_response.get("email") == "unavailable"
    assert json_response.get("username") == "unavailable"


    # test 2
    # making a request with data that does not exists
    probe_data_which_does_not_exist = {
        "email": "testuser2@example.com",
        "username": "testuser2",
    }
    # make the request
    response = await client.post(
        "/auth/probe-user-existence",
        json=probe_data_which_does_not_exist  # Use json instead of data for a JSON body
    )
    # Assertions
    assert response.status_code == 200
    json_response = response.json()
    assert json_response.get("email") == "available"
    assert json_response.get("username") == "available"


@pytest.mark.asyncio
async def test_send_email_verification_code(client__fixture: AsyncClient):    
    # fetch the client generator
    client_gen =  client__fixture
    # get the yield client object
    client = await client_gen.__anext__()

    # Define a post data
    post_data = {
        "email": "crankgig@gmail.com",
        "username": "crank",
    }
    # request a verification code
    response = await client.post(
        "/auth/send-email-verification-code",
        json=post_data  # Use json instead of data for a JSON body
    )

    # Assertions
    assert response.status_code == 200
    json_response = response.json()
    assert json_response.get("message") == "A new verification code has been sent to your email."

    # make a temporary pause
    await asyncio.sleep(60) #one minute

    # request another to verify that the expiry works 
    # the other code has expired
    response = await client.post(
        "/auth/send-email-verification-code",
        json=post_data  # Use json instead of data for a JSON body
    )    
    # Assertions
    assert response.status_code == 200
    json_response = response.json()
    assert json_response.get("message") == "Please wait before requesting a new code."


@pytest.mark.asyncio
async def test_confirm_email_verification_code(client__fixture: AsyncClient, redis_client__fixture):    
    # Fetch the client generator
    client_gen = client__fixture
    # Get the yield client object
    client = await client_gen.__anext__()

    # fetch the redis client generator
    redis_client_gen =  redis_client__fixture
    # get the yield redis client object
    redis_client = await redis_client_gen.__anext__()

    # Define the post data for sending the email verification code
    send_code_data = {
        "email": "crankgig@gmail.com",
        "username": "crank",
    }

    # Request a verification code
    response = await client.post(
        "/auth/send-email-verification-code",
        json=send_code_data  # Use json instead of data for a JSON body
    )

    # Assertions for sending the verification code
    assert response.status_code == 200
    json_response = response.json()
    assert json_response.get("message") == "A new verification code has been sent to your email."

    # Retrieve the code directly from Redis (this simulates the user entering the code they received)
    user_key = f'{send_code_data["email"]}:email_verification'
    verification_code = await redis_client.hget(user_key, "email_verification")
    assert verification_code is not None

    # Define the post data for confirming the verification code
    confirm_code_data = {
        "email": send_code_data["email"],
        "verification_code": verification_code.decode('utf-8')
    }

    # Confirm the verification code
    response = await client.post(
        "/auth/confirm-email-verification-code",
        json=confirm_code_data  # Use json instead of data for a JSON body
    )

    # Assertions for confirming the verification code
    assert response.status_code == 200
    json_response = response.json()
    assert json_response.get("email_status") == "Verified"
    assert json_response.get("message") == "The email has been successfully verified."

    # Test with an incorrect code
    incorrect_code_data = {
        "email": send_code_data["email"],
        "verification_code": "12345"  # Assuming this is not the correct code
    }

    # Try confirming with the incorrect code
    response = await client.post(
        "/auth/confirm-email-verification-code",
        json=incorrect_code_data  # Use json instead of data for a JSON body
    )

    # Assertions for the incorrect code
    assert response.status_code == 400
    json_response = response.json()
    assert json_response.get("detail") == "Invalid verification code."

    # Test with an expired code
    await asyncio.sleep(90)  # Wait for 90 seconds to let the code expire assuming expiry time is 60 seconds

    # Try confirming with the expired code
    response = await client.post(
        "/auth/confirm-email-verification-code",
        json=confirm_code_data  # Re-use the correct code data
    )

    # Assertions for the expired code
    assert response.status_code == 404
    json_response = response.json()
    assert json_response.get("detail") == "Verification code not found or expired."
