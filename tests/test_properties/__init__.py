from sqlalchemy.ext.asyncio import AsyncSession

from .test_processing import property_payload
from property_street_backend.app.models import (
    User, 
    Asset,
)
from property_street_backend.tests.auth.test_create_agent import create_test_agent
from property_street_backend.app.controllers.assets.relationship_handler import apply_model



async def create_test_asset(db: AsyncSession, agent_id=None, with_feature: bool = True) -> Asset:
    """
    Helper function to create a test asset for other tests.
    """
    if not agent_id:
        created_agent: User = await create_test_agent(db)
        agent_id = created_agent.id

    payload = property_payload(agent_id, with_feature)
    return await apply_model(Asset, db, payload)
