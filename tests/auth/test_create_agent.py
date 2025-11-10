import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from .test_user_creation import user_data
from property_street_backend.app.models import User
from property_street_backend.app.controllers.auth.services import (
    create_agent,
    verify_password,
)
from property_street_backend.app.controllers.actors.schemas import AgentResponseSchema


async def create_test_agent(db:AsyncSession):
    return await create_agent(
        db = db, 
        user_data = user_data
    )


@pytest.mark.asyncio
async def test_create_agent(get_test_db__fixture: AsyncSession):
    # fetch the testdb
    test_db = get_test_db__fixture
    try:
        created_agent: User = await create_test_agent(test_db)
        
        # assertions 
        assert created_agent.username == user_data.username
        assert created_agent.email == user_data.email
        assert created_agent.first_name == user_data.first_name
        assert created_agent.last_name == user_data.last_name
        assert created_agent.user_role.value == 'agent'
        assert verify_password(
            plain_password = user_data.password,
            hashed_password = created_agent.password_hash        
        )
    finally: 
        # close the session
        await test_db.close()