import pytest
from httpx import AsyncClient
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import User



@pytest.mark.asyncio
async def test_register_user(
    client__fixture
):
    httpx_client: AsyncClient = client__fixture['http_client']
    test_db: AsyncSession = client__fixture['db']

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