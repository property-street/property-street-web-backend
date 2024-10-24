import pytest
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import (
    Tag,
    Asset, 
    AssetFeature, 
    asset_tag_association,
)
from property_street_backend.tests.auth.test_create_agent import (
    create_test_agent as create_agent
)
from property_street_backend.tests.activity.test_asset_creation import (
    create_test_asset,
    create_test_asset_feature,
)
from property_street_backend.app.schemas.auth_schemas import UserRegistrationSchema
from property_street_backend.app.controllers.activity.agent_crud_processing import (
    process_asset,
    remove_tags_from_asset,
)
from property_street_backend.tests.activity.test_objects import (
    feature_obj,
    no_feature_obj
)



@pytest.mark.asyncio
async def test_create_asset_with_feature(get_test_db__fixture: AsyncSession):
    try:
        test_db = await get_test_db__fixture

        # Define a test agent
        user_data = UserRegistrationSchema(
            email="agent@example.com",
            username="agentuser",
            password="password123"
        )

        # Call the create_user function
        created_agent = await create_agent(test_db, user_data)

        # modify feature object to include an agent's id
        feature_obj[0]['db_table_id'] = created_agent.id
        
        # Process asset with features
        await process_asset(feature_obj, test_db)

        # Fetch the created asset from the database
        result = await test_db.execute(select(Asset).filter(Asset.title == feature_obj[4]['fields']['title']))
        created_asset = result.scalars().first()

        # Assertions
        assert created_asset is not None
        assert created_asset.title == feature_obj[4]['fields']['title']
        assert created_asset.has_features is True

        # Check the features
        result = await test_db.execute(select(AssetFeature).filter(AssetFeature.asset_id == created_asset.id))
        asset_feature = result.scalars().first()
        assert asset_feature is not None
    finally:
        await test_db.close()

@pytest.mark.asyncio
async def test_create_asset_with_no_feature(get_test_db__fixture: AsyncSession):
    try:
        test_db = await get_test_db__fixture

        # Define a test agent
        user_data = UserRegistrationSchema(
            email="agent@example.com",
            username="agentuser",
            password="password123"
        )

        # Call the create_user function
        created_agent = await create_agent(test_db, user_data)

        # modify feature object to include an agent's id
        no_feature_obj[0]['db_table_id'] = created_agent.id
        
        # Process asset with features
        await process_asset(no_feature_obj, test_db)

        # Fetch the created asset from the database
        result = await test_db.execute(select(Asset).filter(Asset.title == no_feature_obj[6]['fields']['title']))
        created_asset = result.scalars().first()

        # Assertions
        assert created_asset is not None
        assert created_asset.title == no_feature_obj[6]['fields']['title']
        assert created_asset.has_features is False
    finally:
        await test_db.close()

@pytest.mark.asyncio
async def test_asset_update(get_test_db__fixture: AsyncSession):
    try:
        test_db = await get_test_db__fixture

        created_asset = await create_test_asset(
            db=test_db
        )

        update_obj = {
            1:{
                # Asset
                "db_delete": False,
                "db_table_id":created_asset.id,
                "db_table_name": "Asset",

                # fields
                "fields": {
                    "title": "4 bedrooms flat",
                    "country": "Barbados",
                    "address": "Montenegro",
                    "status": "Auction",
                    "category": "Condo",
                    "description": "<span>bulaba/span>",
                },
            }
        }

        # Process asset for update
        await process_asset(update_obj, test_db)

        # Fetch of updated asset
        asset_fields = update_obj[1]["fields"]
        result = await test_db.execute(
            select(Asset).filter(Asset.title == asset_fields['title'])
        )
        asset = result.scalars().first()
        
        # assertions
        assert asset is not None
        assert asset.country == asset_fields['country']
        assert asset.address == asset_fields['address']
        assert asset.status == asset_fields['status']
        assert asset.category == asset_fields['category']
        assert asset.description == asset_fields['description']
    finally:
        await test_db.close()
    pass

@pytest.mark.asyncio
async def test_asset_delete(get_test_db__fixture: AsyncSession):
    try:
        test_db = await get_test_db__fixture

        created_asset = await create_test_asset(
            db=test_db
        )

        created_asset_feature = await create_test_asset_feature(
            db=test_db,
            asset_id = created_asset.id
        )

        delete_obj = {
            1:{
                # Asset
                "db_delete": True,
                "db_table_id":created_asset.id,
                "db_table_name": "Asset",
            }
        }

        # Process asset for update
        await process_asset(delete_obj, test_db)

        # Fetch of deleted asset
        result = await test_db.execute(
            select(Asset).filter(Asset.id == created_asset.id)
        )
        asset = result.scalars().first()
        # Fetch of deleted asset feature to check if delete cascaded
        result = await test_db.execute(
            select(AssetFeature).filter(AssetFeature.id == created_asset_feature.id)
        )
        asset_feature = result.scalars().first()
        
        # assertions
        assert asset is None
        assert asset_feature is None
    finally:
        await test_db.close()
    pass

@pytest.mark.asyncio
async def test_tag_delete_from_asset(get_test_db__fixture: AsyncSession):
    try:
        test_db = await get_test_db__fixture

        # Define a test agent
        user_data = UserRegistrationSchema(
            email="agent@example.com",
            username="agentuser",
            password="password123"
        )

        # Call the create_user function
        created_agent = await create_agent(test_db, user_data)

        # Modify feature object to include an agent's id
        feature_obj[0]['db_table_id'] = created_agent.id

        # Process asset with features
        await process_asset(feature_obj, test_db)

        # Fetch the created asset from the database
        result = await test_db.execute(select(Asset).filter(Asset.title == feature_obj[4]['fields']['title']))
        created_asset = result.scalars().first()

        # Fetch the first tag from the table
        result = await test_db.execute(select(Tag).filter(Tag.name == feature_obj[1]['fields']['name']))
        tag1 = result.scalars().first()

        # Fetch the second tag from the table
        result = await test_db.execute(select(Tag).filter(Tag.name == feature_obj[2]['fields']['name']))
        tag2 = result.scalars().first()

        # Remove the tags from the asset
        await remove_tags_from_asset(
            session=test_db,
            asset_id=created_asset.id,
            tag_ids=[tag1.id, tag2.id]
        )

        # Assert that the tags are no longer associated with the asset
        result = await test_db.execute(
            select(asset_tag_association).where(
                asset_tag_association.c.asset_id == created_asset.id,
                asset_tag_association.c.tag_id.in_([tag1.id, tag2.id])
            )
        )
        removed_tags = result.fetchall()

        # There should be no rows found, indicating that the tags are removed
        assert len(removed_tags) == 0, "Tags were not removed from the asset"
        
    finally:
        await test_db.close()

