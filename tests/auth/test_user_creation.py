import pytest
import asyncio

from httpx import AsyncClient
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import User
from property_street_backend.app.controllers.auth import create_user
from property_street_backend.app.schemas.auth_schemas import UserRegistrationSchema


async def create_test_user(
    db: AsyncSession,
    user_data = UserRegistrationSchema(
        email="test@example.com",
        username="testuser",
        password="password123"
    )
):

    return await create_user(db, user_data)


@pytest.mark.asyncio
async def test_controller_create_user(
    get_test_db__fixture
):
    test_db = await get_test_db__fixture.__anext__()
    assert isinstance(test_db, AsyncSession)

    # Define a test user
    user_data = UserRegistrationSchema(
        email="test@example.com",
        username="testuser",
        password="password123"
    )
    
    # Call the create_user function
    created_user = await create_user(test_db, user_data)

    # testing the become agent method of the user
    await created_user.become_agent(
        session = test_db
    )
    print(f'***agent_id: {created_user.agent_profile_id}')


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


@pytest.mark.asyncio
async def test_route_create_user(client__fixture_with_onlyDB_fixture: tuple):
    # fetch the client generator
    client_gen =  client__fixture_with_onlyDB_fixture
    # get the yield client object
    client, test_db = await client_gen.__anext__()

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
async def test_route_probe_user_existence(client__fixture):
    # fetch the client generator
    async for fixture_obj in client__fixture:
        # get the yield client object
        client = fixture_obj['http_client']
        break

    # Define a post data
    post_data = {
        "email": "testuser@example.com",
        "username": "testuser",
        "password": "password123",
    }
    # sign the user up
    await client.post(
        "/auth/register",
        json=post_data  
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
async def test_send_email_verification_code_hash(client__fixture: tuple):    
    # fetch the client generator
    client_gen =  client__fixture
    # get the yield client object
    client, redis_client = await client_gen.__anext__()

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
    await asyncio.sleep(60) #60 seconds; 1 minute

    # request another to verify that the expiry works 
    # the other code has expired
    response = await client.post(
        "/auth/send-email-verification-code",
        json=post_data  # Use json instead of data for a JSON body
    )    
    # Assertions
    assert response.status_code == 200
    json_response = response.json()
    assert json_response.get("message") == "A new verification code has been sent to your email."


@pytest.mark.asyncio
async def test_confirm_email_verification_code(client__fixture: tuple):    
    # Fetch the client generator
    client_gen = client__fixture
    # Get the yield client objects
    client, redis_client = await client_gen.__anext__()

    # Define the post data for sending the email verification code
    send_code_data = {
        "email": "wisdomscott98@gmail.com",
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

    # ** testing the confirm_email_verification_code function
    # ...

    # Case 1: Correct code and full name parsing
    confirm_code_data = {
        "email": send_code_data["email"],
        "verification_code": verification_code.decode('utf-8'),
        "username": "crank",
        "fullname": "John Doe",
        "password": "strongpassword",
        "client_type": "Agent"
    }

    # Confirm the verification code with correct data
    response = await client.post(
        "/auth/confirm-email-verification-code",
        json=confirm_code_data  # Use json instead of data for a JSON body
    )

    # Assertions for confirming the verification code
    assert response.status_code == 200
    json_response = response.json()
    assert json_response.get("email_status") == "Verified"
    assert json_response.get("message") == "The email has been successfully verified and the user has been registered."
    assert json_response.get("user_id") is not None  # Ensure user ID is returned


    # Case 2: Expired verification code

    # Try confirming again
    response = await client.post(
        "/auth/confirm-email-verification-code",
        json=confirm_code_data  # Re-use the correct code data
    )
    # Assertions for the expired code
    assert response.status_code == 404
    json_response = response.json()
    assert json_response.get("detail") == "Verification code not found or expired."

