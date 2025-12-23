import pytest
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import (
    Asset,
)
from property_street_backend.config.settings import BETA_LAUNCH_PROPERTY_LIMIT
from property_street_backend.tests.auth.test_create_agent import create_test_agent
from property_street_backend.tests.test_properties.test_processing import property_payload
from property_street_backend.app.controllers.assets.relationship_handler import apply_model

@pytest.mark.asyncio
async def test_beta_agent_asset_limit_enforced(get_test_db__fixture):
    """Create assets using apply_model for a beta agent. The 6th creation should fail."""
    test_db: AsyncSession = get_test_db__fixture
    limit = BETA_LAUNCH_PROPERTY_LIMIT
    try:
        # create agent and mark as beta
        created_agent = await create_test_agent(test_db)
        test_db.add(created_agent)
        await test_db.commit()
        await test_db.refresh(created_agent)

        for _ in range(limit):
            payload = property_payload(created_agent.id)
            inst = await apply_model(Asset, test_db, payload)
            assert inst is not None
            await asyncio.sleep(1) # avois same public id on cloud_images

        # Sixth creation must fail due to beta agent limit
        with pytest.raises(Exception):
            payload = property_payload(created_agent.id)
            await apply_model(Asset, test_db, payload)
    finally:
        await test_db.close() 