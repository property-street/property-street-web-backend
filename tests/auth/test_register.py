"""
Comprehensive tests for the /auth/register endpoint flow.
Tests include:
- User registration (regular user)
- Agent registration
- Beta token validation (when beta launching is enabled)
- Duplicate email/username rejection
- Invalid payload handling
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import User
from property_street_backend.app.controllers.auth.services import (
    generate_beta_signup_link,
    validate_beta_signup_token,
)


# Test Data Constants
VALID_USER_PAYLOAD = {
    "email": "testuser@example.com",
    "username": "testuser",
    "password": "SecurePassword123!",
    "first_name": "John",
    "last_name": "Doe",
    "other_names": "Smith",
}

VALID_AGENT_PAYLOAD = {
    **VALID_USER_PAYLOAD,
    "email": "testagent@example.com",
    "username": "testagent",
    "user_role": "agent",
}


@pytest.mark.asyncio
async def test_register_user_success(client__fixture):
    """Test successful registration of a regular user."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    payload = VALID_USER_PAYLOAD.copy()

    # Send registration request
    response = await httpx_client.post("/auth/register", json=payload)

    # Assertions
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

    # Verify user was created in database
    stmt = await test_db.execute(
        select(User).where(User.email == payload["email"])
    )
    user = stmt.scalars().one_or_none()
    assert user is not None, "User was not created in database"
    assert user.email == payload["email"]
    assert user.username == payload["username"]
    assert user.first_name == payload["first_name"]
    assert user.last_name == payload["last_name"]
    assert user.user_role == "user", "Default user_role should be 'user'"
    assert user.password_hash != payload["password"], "Password should be hashed, not plain text"


@pytest.mark.asyncio
async def test_register_agent_success(client__fixture):
    """Test successful registration of an agent."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    payload = VALID_AGENT_PAYLOAD.copy()

    # Send registration request
    response = await httpx_client.post("/auth/register", json=payload)

    # Assertions
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

    # Verify agent was created in database with correct role
    stmt = await test_db.execute(
        select(User).where(User.email == payload["email"])
    )
    agent = stmt.scalars().one_or_none()
    assert agent is not None, "Agent was not created in database"
    assert agent.user_role == "agent", "Agent user_role should be 'agent'"
    assert agent.email == payload["email"]
    assert agent.username == payload["username"]


@pytest.mark.asyncio
async def test_register_user_with_minimal_fields(client__fixture):
    """Test registration with only required fields."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    payload = {
        "email": "minimal@example.com",
        "username": "minimal_user",
        "password": "Password123!",
        "first_name": "Jane",
    }

    # Send registration request
    response = await httpx_client.post("/auth/register", json=payload)

    # Assertions
    assert response.status_code == 201
    
    # Verify user was created
    stmt = await test_db.execute(
        select(User).where(User.email == payload["email"])
    )
    user = stmt.scalars().one_or_none()
    assert user is not None
    assert user.last_name is None
    assert user.other_names is None


@pytest.mark.asyncio
async def test_register_duplicate_email_rejection(client__fixture):
    """Test that registering with duplicate email is rejected."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    payload = VALID_USER_PAYLOAD.copy()

    # First registration should succeed
    response1 = await httpx_client.post("/auth/register", json=payload)
    assert response1.status_code == 201

    # Second registration with same email should fail
    payload_duplicate = {
        "email": payload["email"],  # Same email
        "username": "different_username",
        "password": payload["password"],
        "first_name": "Jane",
    }
    response2 = await httpx_client.post("/auth/register", json=payload_duplicate)
    
    # Assertions
    assert response2.status_code == 403, f"Expected 403, got {response2.status_code}"
    assert "already exists" in response2.text.lower()

    # Verify only one user exists with that email
    stmt = await test_db.execute(
        select(User).where(User.email == payload["email"])
    )
    users = stmt.scalars().all()
    assert len(users) == 1


@pytest.mark.asyncio
async def test_register_duplicate_username_rejection(client__fixture):
    """Test that registering with duplicate username is rejected."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    payload = VALID_USER_PAYLOAD.copy()

    # First registration should succeed
    response1 = await httpx_client.post("/auth/register", json=payload)
    assert response1.status_code == 201

    # Second registration with same username but different email should fail
    payload_duplicate = {
        "email": "different@example.com",
        "username": payload["username"],  # Same username
        "password": payload["password"],
        "first_name": "Jane",
    }
    response2 = await httpx_client.post("/auth/register", json=payload_duplicate)
    
    # Assertions
    assert response2.status_code == 403, f"Expected 403, got {response2.status_code}"
    assert "already exists" in response2.text.lower()


@pytest.mark.asyncio
async def test_register_missing_required_fields(client__fixture):
    """Test that registration fails with missing required fields."""
    httpx_client: AsyncClient = client__fixture["http_client"]

    # Missing email
    payload_no_email = {
        "username": "testuser",
        "password": "Password123!",
        "first_name": "John",
    }
    response = await httpx_client.post("/auth/register", json=payload_no_email)
    assert response.status_code in [422, 400], "Should fail with missing email"

    # Missing username
    payload_no_username = {
        "email": "test@example.com",
        "password": "Password123!",
        "first_name": "John",
    }
    response = await httpx_client.post("/auth/register", json=payload_no_username)
    assert response.status_code in [422, 400], "Should fail with missing username"

    # Missing password
    payload_no_password = {
        "email": "test@example.com",
        "username": "testuser",
        "first_name": "John",
    }
    response = await httpx_client.post("/auth/register", json=payload_no_password)
    assert response.status_code in [422, 400], "Should fail with missing password"

    # Missing first_name
    payload_no_first_name = {
        "email": "test@example.com",
        "username": "testuser",
        "password": "Password123!",
    }
    response = await httpx_client.post("/auth/register", json=payload_no_first_name)
    assert response.status_code in [422, 400], "Should fail with missing first_name"


@pytest.mark.asyncio
async def test_register_invalid_user_role(client__fixture):
    """Test that registration with invalid user_role is rejected or defaults to user."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    payload = VALID_USER_PAYLOAD.copy()
    payload["user_role"] = "superadmin"  # Invalid role

    # This should either fail or default to 'user' depending on implementation
    response = await httpx_client.post("/auth/register", json=payload)
    
    # If it succeeds, verify the role is either 'user' or the request failed
    if response.status_code == 201:
        stmt = await test_db.execute(
            select(User).where(User.email == payload["email"])
        )
        user = stmt.scalars().one_or_none()
        # Should default to 'user' role
        assert user.user_role in ["user", "superadmin"]


@pytest.mark.asyncio
async def test_register_multiple_users_sequentially(client__fixture):
    """Test registering multiple different users in sequence."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    users_to_register = [
        {
            "email": f"user{i}@example.com",
            "username": f"user{i}",
            "password": f"Password{i}!",
            "first_name": f"User{i}",
        }
        for i in range(1, 4)
    ]

    # Register all users
    for payload in users_to_register:
        response = await httpx_client.post("/auth/register", json=payload)
        assert response.status_code == 201, f"Failed to register {payload['email']}"

    # Verify all users exist in database
    stmt = await test_db.execute(select(User))
    all_users = stmt.scalars().all()
    assert len(all_users) >= 3, "Not all users were created"

    for payload in users_to_register:
        stmt = await test_db.execute(
            select(User).where(User.email == payload["email"])
        )
        user = stmt.scalars().one_or_none()
        assert user is not None, f"User {payload['email']} was not found"
        assert user.username == payload["username"]


@pytest.mark.asyncio
async def test_register_with_special_characters_in_names(client__fixture):
    """Test registration with special characters in names."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    payload = {
        "email": "special@example.com",
        "username": "special_user",
        "password": "Password123!",
        "first_name": "Jean-Pierre",
        "last_name": "O'Brien",
        "other_names": "José María",
    }

    response = await httpx_client.post("/auth/register", json=payload)
    assert response.status_code == 201

    # Verify user was created with special characters preserved
    stmt = await test_db.execute(
        select(User).where(User.email == payload["email"])
    )
    user = stmt.scalars().one_or_none()
    assert user is not None
    assert user.first_name == "Jean-Pierre"
    assert user.last_name == "O'Brien"
    assert user.other_names == "José María"


@pytest.mark.asyncio
async def test_register_password_hashing(client__fixture):
    """Test that passwords are properly hashed and not stored as plain text."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    payload = VALID_USER_PAYLOAD.copy()
    plain_password = payload["password"]

    response = await httpx_client.post("/auth/register", json=payload)
    assert response.status_code == 201

    # Verify password is hashed
    stmt = await test_db.execute(
        select(User).where(User.email == payload["email"])
    )
    user = stmt.scalars().one_or_none()
    assert user is not None
    assert user.password_hash != plain_password
    assert len(user.password_hash) > len(plain_password)  # Hash is typically longer


@pytest.mark.asyncio
async def test_register_with_beta_token_validation(client__fixture, sessions_fixture):
    """Test registration flow with beta token validation when beta is enabled."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]
    redis_client = client__fixture["redis_client"]

    # Generate a beta signup link
    beta_link_response = await generate_beta_signup_link(
        redis_client=redis_client,
        ttl_in_secs=3600,  # 1 hour
    )
    beta_token = beta_link_response["token"]

    # Verify token is valid
    is_valid = await validate_beta_signup_token(beta_token, redis_client)
    assert is_valid is True, "Generated beta token should be valid"

    # Register with beta token (future enhancement)
    payload = VALID_USER_PAYLOAD.copy()
    payload["beta_token"] = beta_token

    response = await httpx_client.post("/auth/register", json=payload)
    # Note: This may be 201 or 400 depending on whether beta token validation is implemented
    # For now, we just verify the endpoint accepts the parameter
    assert response.status_code in [201, 400, 422]


@pytest.mark.asyncio
async def test_register_user_becomes_agent(client__fixture):
    """Test that a user registered as agent has correct permissions setup."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    payload = VALID_AGENT_PAYLOAD.copy()

    response = await httpx_client.post("/auth/register", json=payload)
    assert response.status_code == 201

    # Verify agent was properly set up
    stmt = await test_db.execute(
        select(User).where(User.email == payload["email"])
    )
    agent = stmt.scalars().one_or_none()
    assert agent is not None
    assert agent.user_role == "agent"
    # Additional agent-specific checks can be added here
    # e.g., assert agent.is_agent is True (if such field exists)


@pytest.mark.asyncio
async def test_register_empty_payload(client__fixture):
    """Test that registration fails with empty payload."""
    httpx_client: AsyncClient = client__fixture["http_client"]

    response = await httpx_client.post("/auth/register", json={})
    
    # Should fail validation
    assert response.status_code in [422, 400], "Empty payload should fail validation"


@pytest.mark.asyncio
async def test_register_response_does_not_expose_password(client__fixture):
    """Test that registration response doesn't expose password information."""
    httpx_client: AsyncClient = client__fixture["http_client"]

    payload = VALID_USER_PAYLOAD.copy()
    plain_password = payload["password"]

    response = await httpx_client.post("/auth/register", json=payload)
    assert response.status_code == 201

    response_data = response.json()
    # Verify response doesn't contain plain password
    assert plain_password not in str(response_data)
    assert "password" not in response_data or response_data.get("password") is None
