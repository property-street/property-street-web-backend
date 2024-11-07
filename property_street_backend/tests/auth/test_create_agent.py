import pytest
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.schemas.auth_schemas import (
    UserRegistrationSchema,
)
from property_street_backend.app.controllers.auth import (
    create_agent,
    verify_password,
)
from property_street_backend.app.models import (
    Agent,
)


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
        created_agent = await create_agent(
            db = test_db, 
            user_data = user_data
        )
        
        # assertions 
        assert created_agent.user.username == user_data.username
        assert created_agent.user.email == user_data.email
        assert verify_password(
            plain_password = user_data.password,
            hashed_password = created_agent.user.password_hash        
        )
    finally:
        await test_db.close()