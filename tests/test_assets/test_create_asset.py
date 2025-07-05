import pytest
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import (
    Tag,
    Area, 
    Asset, 
    AssetFeature,
    AssetCloudImage,
    CloudImageDetail,
)
from property_street_backend.app.controllers.assets.schemas import (
    AreaSchema,
    CloudImageSchema,
    AssetFetchResponseSchema,
)
from property_street_backend.app.schemas.asset_schemas import (
    AssetSchema
)
from property_street_backend.app.controllers.assets.enums import AvailabilityStatus
from property_street_backend.tests.auth.test_create_agent import create_test_agent
from property_street_backend.tests.activity.test_controller.test_objects import (
    cloud_image_template,
    area_template,
    tags_template,
    asset_data_template
)

# test utility functions

async def create_test_asset(db: AsyncSession, agent_id=None):
    """
    Helper function to create a test asset for other tests.
    """
    # Prepare and create tag instances
    result = await db.execute(select(Tag).filter(Tag.name.in_(tags_template)))
    existing_tags = result.scalars().all()
    # Get names of already existing tags
    existing_tag_names = {tag.name for tag in existing_tags}

    # Create only new tags
    new_tags = [Tag(name=name) for name in tags_template if name not in existing_tag_names]
    db.add_all(new_tags)
    await db.flush()  # Ensure IDs are available

    # Combine all tags
    asset_tags = existing_tags + new_tags

    # Cover image
    cloud_image_template['public_id'] = 'public_id_cover_image'
    cover_image_data = cloud_image_template
    CloudImageSchema.model_validate(cover_image_data)
    asset_cover_image = CloudImageDetail(**cover_image_data)

    # Asset cloud image
    cloud_image_template['public_id'] =  'public_id_asset_cloud_image'
    cloud_image_data = cloud_image_template
    CloudImageSchema.model_validate(cloud_image_data)
    asset_cloud_image = AssetCloudImage(**cloud_image_data)

    # area data
    area_data = {**area_template}
    AreaSchema.model_validate(area_data)
    asset_area = Area(**area_data)

    # Create the asset
    new_asset = Asset(
        **asset_data_template,
        area = asset_area,
        agent_id=agent_id,
        cover_image=asset_cover_image,
        cloud_images=[asset_cloud_image],
    )

    new_asset.tags = asset_tags
    db.add(new_asset)
    await db.flush()  # Assign an ID to the new_asset before adding many-to-many

    # Assign tags to asset after both sides have IDs

    # Save changes
    await db.commit()
    await db.refresh(new_asset)

    return new_asset



@pytest.mark.asyncio
async def test_create_asset_with_no_feature(get_test_db__fixture): 
    try:
        # fetch the testdb
        async for test_db in get_test_db__fixture:
            test_db: AsyncSession
            break

        # Create a test agent/user
        created_agent = await create_test_agent(test_db)
        assert created_agent is not None

        # Create a test asset
        created_asset: Asset = await create_test_asset(test_db,created_agent.id)
        assert created_asset is not None
        assert created_asset.title == asset_data_template['title']
        # direct testing of the AssetSchema schema on an asset instance 
        schema = AssetFetchResponseSchema.model_validate(created_asset)
        print(schema)

        # set the cloud_images to None, and set a feature
        created_asset.cloud_images = []

        del cloud_image_template['public_id']
        created_asset.features = [AssetFeature(
            title = 'feature1',
            cloud_images = [
                AssetCloudImage(
                    **cloud_image_template,
                    public_id = f'asset_feature_public_id{i}'
                ) for i in range(2)
            ]
        )]
        test_db.add(created_asset)
        await test_db.commit()
        await test_db.refresh(created_asset)
        AssetSchema.model_validate(created_asset)
        
        # Create an asset feature linked to the asset
        # created_feature = await create_test_asset_feature(test_db, created_asset.id)
        # assert created_feature is not None
        # assert created_feature.title == "Test Feature"
    # 
        # # Create a cloud image detail linked to the asset
        # created_image = await create_test_cloud_image_detail(test_db, created_asset.id)
        # assert created_image is not None
        # assert created_image.public_id == "test_image_123"
        # 
        # # Verify that the asset was actually created in the database
        # result = await test_db.execute(
        #     select(Asset).filter(Asset.title == "Test Asset")
        # )
        # asset = result.scalars().first()
        # assert asset is not None
    # 
        # # Verify that the asset feature was actually created in the database
        # result = await test_db.execute(
        #     select(AssetFeature).filter(AssetFeature.title == "Test Feature")
        # )
        # feature = result.scalars().first()
        # assert feature is not None
        # assert feature.asset_id == created_asset.id
    # 
        # # Verify that the cloud image detail was actually created in the database
        # result = await test_db.execute(
        #     select(AssetCloudImage).filter(AssetCloudImage.public_id == "test_image_123")
        # )
        # image = result.scalars().first()
        # assert image is not None
        # assert image.asset_id == created_asset.id
    finally: 
        await test_db.close()