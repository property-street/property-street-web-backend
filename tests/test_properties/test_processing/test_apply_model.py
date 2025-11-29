import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from . import property_payload
from property_street_backend.app.models import (
    User, 
    Asset,
)
from tests.activity.test_controller.test_objects import (
    area_template,
    tags_template,
    asset_data_template
)
from property_street_backend.tests.auth.test_create_agent import create_test_agent
from property_street_backend.app.controllers.assets.schemas import AssetResponseSchema
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



@pytest.mark.asyncio
async def test_create_with_apply_model(get_test_db__fixture): 
    try:
        # fetch the testdb
        test_db: AsyncSession = get_test_db__fixture

        # Property with featured images
        prpty_with_feat_imgs: Asset = await create_test_asset(test_db)
        agent_id = prpty_with_feat_imgs.agent_id
        id = prpty_with_feat_imgs.id

        assert prpty_with_feat_imgs
        assert prpty_with_feat_imgs is not None
        assert prpty_with_feat_imgs.title == asset_data_template['title']
        assert prpty_with_feat_imgs.has_features
        assert all((db_tag.name in plod_tag['name'] for plod_tag in tags_template) for db_tag in prpty_with_feat_imgs.tags)
        assert prpty_with_feat_imgs.area.country == area_template['country']
        assert prpty_with_feat_imgs.features[0].title == "Feature"
        AssetResponseSchema.model_validate(prpty_with_feat_imgs)
        await test_db.delete(prpty_with_feat_imgs)
        await test_db.commit()
        assert not await test_db.get(Asset, id)

        # Property with unfeatured images
        prpty_no_feat_imgs: Asset = await create_test_asset(test_db, agent_id, with_feature=False)
        assert prpty_no_feat_imgs
        assert len(prpty_no_feat_imgs.cloud_images) == 1
        # AssetResponseSchema.model_validate(prpty_no_feat_imgs)
    finally: 
        await test_db.close()