import pytest
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession


from property_street_backend.tests.auth.test_create_agent import create_test_agent

@pytest.mark.asyncio
async def test_latest_collection(client__fixture):
    async for fixture_obj in client__fixture:
        test_db: AsyncSession = fixture_obj["db"]
        redis_client: Redis = fixture_obj["redis_client"]
        break
    
    # Create a test agent/user
    created_agent = await create_test_agent(test_db)