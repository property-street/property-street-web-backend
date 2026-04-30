import pytest
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient

from . import create_test_user, user_data
from property_street_backend.app.models import User
from property_street_backend.app.controllers.auth.services import create_user, authenticate_user
from property_street_backend.app.schemas.auth_schemas import UserRegistrationSchema, SigninResponse


@pytest.mark.asyncio
async def test_controller_authenticate_user(get_test_db__fixture):
    test_db = get_test_db__fixture   

    # Define a test user
    user_data = UserRegistrationSchema(
        email="test@example.com",
        username="testuser",
        password="password123",
        first_name='John',
        last_name='Doe'
    )

    # Call the create_user function
    created_user: User = await create_user(test_db, user_data)

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

    
    # Testing for user authentication 
    user = await authenticate_user(
        test_db,
        user_data.username,
        user_data.password
    )
    assert user != None


async def signin_user(client: AsyncClient, db: AsyncSession):
    user = await create_test_user(db)
    response = await client.post(
        "/auth/signin",
        json={
            "email": user.email,
            "password": user_data.password,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["access_token"]
    assert payload["refresh_token"]
    assert payload["refresh_session_id"]
    assert "session_id" in client.cookies
    return user, payload


@pytest.mark.asyncio
async def test_signin(client__fixture):
    # Extract the fisxture object
    test_db: AsyncSession = client__fixture['db']
    client: AsyncClient = client__fixture['http_client']

    user, payload = await signin_user(client, test_db)
    assert user
    assert payload