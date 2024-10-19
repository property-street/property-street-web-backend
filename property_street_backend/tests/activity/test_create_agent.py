import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.schemas.auth_schemas import (
    UserRegistrationSchema,
)
from property_street_backend.app.controllers.auth import create_user
from property_street_backend.app.controllers.auth import get_password_hash

async def create_test_agent(db:AsyncSession, user_data:UserRegistrationSchema):

    """
    Helper function to create and return a test agent.
    """
    
    # Call the create_user function
    created_user = await create_user(db, user_data)
    
    # call the become agent on the created user
    await created_user.become_agent(db)

    return created_user.agent_profile    


@pytest.mark.asyncio
async def test_create_agent(get_test_db__fixture: AsyncSession):
    try:
        # fetch the testdb
        test_db = await get_test_db__fixture

        user_data = UserRegistrationSchema(
            email="agent@example.com",
            username="agentuser",
            password="password123"
        )
        created_agent = await create_test_agent(test_db, user_data)

        # Assertions
        assert created_agent is not None
        assert created_agent.user.email == user_data.email
        assert created_agent.user.username == user_data.username
        assert created_agent.user.password_hash != user_data.password  # Ensure the password
    finally:
        await test_db.close()