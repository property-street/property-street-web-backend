import json
import pytest
from typing import List
from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession


from property_street_backend.app.models import (
    Tag,
    Area,
    User,
    Asset, 
    AssetCloudImage,
    CloudImageDetail,
)
from property_street_backend.app.initiator import logger
from property_street_backend.app.controllers.activity import (
    auto_category_hset_key,
    newly_created_asset_set_key, 
)
from property_street_backend.tests.auth.test_create_agent import (
    create_test_agent
)
from .test_fetch_recent_assets import pre_commit_test_asset_collection
from property_street_backend.app.controllers.assets.services import eager_asset_load
from property_street_backend.app.controllers.assets.schemas import AssetResponseSchema


@pytest.mark.asyncio
async def test_unverified_properties(client__fixture):

    # Unpack the client and test database from the fixture
    httpx_client: AsyncClient = client__fixture['http_client'] 
    test_db: AsyncSession = client__fixture['db']
    redis_client: Redis = client__fixture['redis_client']

    # Create a test agent/user
    created_agent: User = await create_test_agent(test_db)

    # Create 10 assets
    test_assets = pre_commit_test_asset_collection(created_agent.id)

    # Save the last 5 asset to the database
    test_db.add_all(test_assets[:5])
    await test_db.commit()

    #----------------------------
    # make http request
    #----------------------------
    await httpx_client.get('/assets/unverified-properties/')