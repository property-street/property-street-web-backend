import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.controllers.assets.models import (
    Asset,
    AssetFeature,
    AssetCloudImage,
)
from property_street_backend.app.models import Area, Tag, CloudImageDetail
from property_street_backend.app.controllers.agents.search import search_agents
from property_street_backend.tests.auth.test_create_agent import create_test_agent
from property_street_backend.app.controllers.assets.schemas import AssetResponseSchema 
from property_street_backend.tests.activity.test_controller.test_objects import cloud_image_template

@pytest.mark.asyncio
async def test_search_agents_basic(client__fixture):
    """
    Tests search_agents() for keyword and numeric matching.
    """
    # fetch the async db session from fixture
    test_db: AsyncSession = client__fixture['db']

    test_agent = await create_test_agent(test_db)


    query1 = {"keywords": [test_agent.username, test_agent.first_name], "numbers": []}
    
    results = await search_agents(query1, test_db)

    assert len(results) == 1
    assert all(r["type"] == "agent" for r in results)