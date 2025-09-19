import pytest
import asyncio

from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import User
from property_street_backend.app.controllers.auth.services import create_user
from property_street_backend.app.schemas.auth_schemas import UserRegistrationSchema


user_data = UserRegistrationSchema(
    email="test@example.com",
    username="testuser",
    password="password123",
    first_name="John",
    last_name="Doe",
)

async def create_test_user(
    db: AsyncSession,
    user_data = user_data
):
    return await create_user(db, user_data)


@pytest.mark.asyncio
async def test_register_user(
    client__fixture
):
    async for fixture_obj in client__fixture:
        httpx_client: AsyncClient = fixture_obj['http_client']
        test_db: AsyncSession = fixture_obj['db']
        break

    # Define a test user
    payload = {
        "email" : "test@example.com",
        "username" : "testuser",
        "password" : "password123",
        "first_name" : "horn",
    }
    
    # post payload for user
    await httpx_client.post(
        '/auth/register',
        json = payload
    )
    stmt = await test_db.execute(
        select(User)
        .where(User.email == payload['email'])
    )
    # asert the user exists
    user = stmt.scalars().one()
    assert user
    await test_db.delete(user)
    await test_db.commit()


    # post payload for agent
    payload['user_role'] = 'agent'
    await httpx_client.post(
        '/auth/register',
        json = payload
    )
    # asert the agent exists
    stmt = await test_db.execute(
        select(User)
        .where(User.email == payload['email'])
    )
    user: User = stmt.scalars().one()
    assert user.user_role == 'agent'



@pytest.mark.asyncio
async def test_probe_user_existence(client__fixture):
    # fetch the client generator
    async for fixture_obj in client__fixture:
        # get the yield client object
        httpx_client: AsyncClient = fixture_obj['http_client']
        test_db: AsyncSession = fixture_obj['db']
        break

    created_user = await create_test_user(test_db)

    # test 1
    # making a request with a username that exists
    payload = {
        "email": "testuser@example.com",
        "username": created_user.username,
    }
    response = await httpx_client.post(
        "/auth/probe-user-existence",
        json=payload  # Use json instead of data for a JSON body
    )
    assert response.status_code == 403


    # test 2
    # making a request with email that exists
    payload = {
        "email": created_user.email,
        "username": "testuser2",
    }
    response = await httpx_client.post(
        "/auth/probe-user-existence",
        json=payload  # Use json instead of data for a JSON body
    )
    assert response.status_code == 403

    # test 3
    # making a request with non-existent data
    payload = {
        "email": 'johndoe@gmail.com',
        "username": "johndoe",
    }
    response = await httpx_client.post(
        "/auth/probe-user-existence",
        json=payload  # Use json instead of data for a JSON body
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_send_and_confirm_email_verification_code(client__fixture):    
    # Fetch the client generator
    async for fixture_obj in client__fixture:
        httpx_client: AsyncClient = fixture_obj['http_client']
        redis_client: Redis = fixture_obj['redis_client']
        break

    # Define the post data for sending the email verification code
    send_code_data = {
        "email": "wisdomscott98@gmail.com",
        "username": "crank",
    }

    # Request a verification code
    response = await httpx_client.post(
        "/auth/send-email-verification-code",
        json=send_code_data  # Use json instead of data for a JSON body
    )
    # Assertions for sending the verification code
    assert response.status_code == 200
    json_response = response.json()
    assert json_response.get("message") == "A new verification code has been sent to your email."


    # Request verification code again
    response = await httpx_client.post(
        "/auth/send-email-verification-code",
        json=send_code_data  # Use json instead of data for a JSON body
    )
    # Assertions for sending the verification code
    assert response.status_code == 302
    json_response = response.json()
    assert json_response['detail']['message'] == "Please wait before requesting a new code."
    assert json_response['detail']['expiry']


    # Retrieve the code directly from Redis (this simulates the user entering the code they received)
    user_key = f'{send_code_data["email"]}:email_verification'
    verification_code: bytes = await redis_client.hget(user_key, "email_verification")
    assert verification_code is not None




    # ** testing the confirm_email_verification_code function
    # ...

    # Case 1: Correct code
    confirm_code_data = {
        "email": send_code_data["email"],
        "code": verification_code.decode('utf-8'),
    }

    # Confirm the verification code with correct data
    response = await httpx_client.post(
        "/auth/confirm-email-verification-code",
        json=confirm_code_data  # Use json instead of data for a JSON body
    )

    # Assertions for confirming the verification code
    assert response.status_code == 200
    json_response = response.json()
    assert json_response['message'] == "The email address has been successfully verified." 


    # Case 2: Expired verification code

    # Try confirming again
    response = await httpx_client.post(
        "/auth/confirm-email-verification-code",
        json=confirm_code_data  # Re-use the correct code data
    )
    # Assertions for the expired code
    assert response.status_code == 404
    json_response = response.json()
    assert json_response["detail"] == "Verification code not found or expired."
