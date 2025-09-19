import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from property_street_backend.app.models import (
    Tag
)
from property_street_backend.app.controllers.activity.agent_crud_processing import (
    get_existing_instance_from_unique_fields,
)

@pytest.mark.asyncio
async def test_create_asset_with_feature(get_test_db__fixture: AsyncSession):
    try:
        test_db = await get_test_db__fixture
        
        tag = Tag(name="first_tag")
        test_db.add(tag)
        await test_db.commit()

        returned_instance = await get_existing_instance_from_unique_fields(
            db = test_db,
            model = Tag,
            obj_data = {"name":"first_tag"}
        )
        assert returned_instance.name == tag.name

        returned_instance = await get_existing_instance_from_unique_fields(
            db = test_db,
            model = Tag,
            obj_data = {"name":"first_tag"}
        )
        assert returned_instance.name == tag.name
    finally:
        await test_db.close()
    pass