import pytest
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.schemas.auth_schemas import (
    UserRegistrationSchema,
)
from property_street_backend.app.models import Agent, User
from property_street_backend.app.controllers.auth import (
    create_agent,
    verify_password,
)
from property_street_backend.app.controllers.actors.schemas import AgentResponseSchema

user_data = UserRegistrationSchema(
    email="agent@example.com",
    username="agentuser",
    password="password123",
    first_name = "agent",
    last_name = "zee"
)

async def create_test_agent(db:AsyncSession):
    return await create_agent(
        db = db, 
        user_data = user_data
    )

@pytest.mark.asyncio
async def test_create_agent(get_test_db__fixture):
    # fetch the testdb
    async for test_db in get_test_db__fixture:
        test_db: AsyncSession
        break
    try:
        created_agent = await create_test_agent(test_db)

        query = (
            select(Agent)
            .options(
                selectinload(Agent.user)
                .selectinload(User.profile_avatar)
            )
            .where(Agent.id == created_agent.id)
        )

        query = await test_db.execute(query)
        agent = query.scalars().first()
        AgentResponseSchema.model_validate(agent)
        
        # assertions 
        assert created_agent.user.username == user_data.username
        assert created_agent.user.email == user_data.email
        assert created_agent.user.first_name == user_data.first_name
        assert created_agent.user.last_name == user_data.last_name
        assert verify_password(
            plain_password = user_data.password,
            hashed_password = created_agent.user.password_hash        
        )
    finally: 
        # close the session
        await test_db.close()