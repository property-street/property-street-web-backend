import pytest
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient

from property_street_backend.app.models import User
from property_street_backend.app.controllers.auth import create_user, authenticate_user
from property_street_backend.app.schemas.auth_schemas import UserRegistrationSchema


@pytest.mark.asyncio
async def test_controller_authenticate_user(get_test_db__fixture: AsyncSession):
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

        
        # Testing for user authentication 
        user = await authenticate_user(
            test_db,
            user_data.username,
            user_data.password
        )
        assert user != None
    finally:
        await test_db.close()
        pass


@pytest.mark.asyncio
async def test_route_signin(client__fixture_with_onlyDB_fixture: tuple):
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

    user_data = UserRegistrationSchema(
        email=post_data['email'],
        username=post_data['username'],
        password=post_data['password']
    )

    # Call the create_user function
    created_user = await create_user(
        test_db, 
        user_data
    )


    signin_post_data = {
        'email': post_data.get("email"),
        'password': post_data.get("password")
    }
    response = await client.post(
        "/auth/signin",
        json=signin_post_data  # Use json instead of data for a JSON body
    )
    
    # Assertions
    assert response.status_code == 200
    json_response = response.json()
    assert json_response.get("token_type") == "bearer"
    assert "access_token" in json_response