import pytest
from datetime import datetime

from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from property_street_backend.app.models import (
    Tag,
    Asset, 
    AssetFeature, 
    AssetCloudImage,
    CloudImageDetail,
)
from property_street_backend.app.schemas.asset_schemas import (
    AssetCreateSchema, 
    AssetFeatureCreateSchema, 
    CloudImageCreateSchema,
)
from property_street_backend.app.schemas.auth_schemas import (
    UserRegistrationSchema, 
)
from property_street_backend.app.controllers.auth import (
    create_agent,
)


async def create_asset(db: AsyncSession, asset_data: AssetCreateSchema):
    new_asset = Asset(
        title=asset_data.title,
        country=asset_data.country,
        address=asset_data.address,
        currency=asset_data.currency,
        amount=asset_data.amount,
        description=asset_data.description,
        category=asset_data.category,
        availability=asset_data.availability,
        #agent_id=asset_data.agent_id,
        status=asset_data.status
    )
    # addition of tags
    tags = []
    for tag_name in asset_data.tags:
        result = await db.execute(select(Tag).filter(Tag.name == tag_name))
        tag = result.scalars().first()
        if not tag:
            # Create new tag if it doesn't exist
            tag = Tag(name=tag_name)
            db.add(tag)
        tags.append(tag)
    
    # Assign tags to the asset
    new_asset.tags = tags

    # addition of cover images
    cover_image_detail = asset_data.cover_image
    cover_image = CloudImageDetail(
        cloud_asset_id=cover_image_detail.cloud_asset_id,
        format=cover_image_detail.format,
        bytes=cover_image_detail.bytes,
        height=cover_image_detail.height,
        public_id=cover_image_detail.public_id,
        secure_url=cover_image_detail.secure_url,
        width=cover_image_detail.width,
    )
    new_asset.cover_image = cover_image

    # database modification
    db.add(new_asset)
    await db.commit()
    await db.refresh(new_asset)
    return new_asset


async def create_asset_feature(db: AsyncSession, feature_data: AssetFeatureCreateSchema):
    new_feature = AssetFeature(
        title=feature_data.title,
        asset_id=feature_data.asset_id
    )
    db.add(new_feature)
    await db.commit()
    await db.refresh(new_feature)
    return new_feature


async def create_cloud_image_detail(db: AsyncSession, image_data: CloudImageCreateSchema):
    new_image = AssetCloudImage(
        cloud_asset_id=image_data.cloud_asset_id,
        format=image_data.format,
        bytes=image_data.bytes,
        height=image_data.height,
        public_id=image_data.public_id,
        secure_url=image_data.secure_url,
        width=image_data.width,
        asset_id=image_data.asset_id
    )
    db.add(new_image)
    await db.commit()
    await db.refresh(new_image)
    return new_image


# test utility functions
async def create_test_asset(db, agent_id=None):
    """
    Helper function to create a test asset for other tests.
    """
    asset_data = AssetCreateSchema(
        title="Test Asset",
        country="Test Country",
        address="123 Test St",
        currency="USD",
        amount=100000.00,
        description="Test description",
        category="House",
        status="auction",
        availability=True,
        agent_id=agent_id,  # Add agent ID if needed
        tags = ["house", "condo"],
        cover_image = CloudImageCreateSchema(
            cloud_asset_id="dkajdlkajdlkajsdkfjasldkfj",
            format="jpg",
            bytes=102400,
            height=800,
            public_id="test_image_123",
            secure_url="https://example.com/test_image.jpg",
            width=600,
        )
    )
    return await create_asset(db, asset_data)


async def create_test_asset_feature(db, asset_id):
    """
    Helper function to create a test asset feature for other tests.
    """
    feature_data = AssetFeatureCreateSchema(
        title="Test Feature",
        asset_id=asset_id  # Link the feature to the asset
    )
    return await create_asset_feature(db, feature_data)


async def create_test_cloud_image_detail(db, asset_id):
    """
    Helper function to create a test cloud image detail.
    """
    image_data = CloudImageCreateSchema(
        cloud_asset_id="dkajdlkajdlkajsdkfjasldkfj",
        format="jpg",
        bytes=102400,
        height=800,
        public_id="test_image_123",
        secure_url="https://example.com/test_image.jpg",
        width=600,
        asset_id=asset_id  # Link to the asset
    )
    return await create_cloud_image_detail(db, image_data)


async def create_test_agent(db):
    """
    Helper function to create a test agent.
    """
    user_data = UserRegistrationSchema(
        email="agent@example.com",
        username="agentuser",
        password="password123",
        first_name="sodovuchi",
        last_name="vinci",
    )
    return await create_agent(db, user_data)



@pytest.mark.asyncio
async def test_controller_create_asset_feature_and_image(get_test_db__fixture: AsyncSession): 
    try:
        # Fetch the test DB session
        test_db = await get_test_db__fixture

        # Create a test agent/user
        created_agent = await create_test_agent(test_db)
        assert created_agent is not None

        # Create a test asset
        created_asset = await create_test_asset(test_db,created_agent.id)
        assert created_asset is not None
        assert created_asset.title == "Test Asset"
        
        # Create an asset feature linked to the asset
        created_feature = await create_test_asset_feature(test_db, created_asset.id)
        assert created_feature is not None
        assert created_feature.title == "Test Feature"

        # Create a cloud image detail linked to the asset
        created_image = await create_test_cloud_image_detail(test_db, created_asset.id)
        assert created_image is not None
        assert created_image.public_id == "test_image_123"
        
        # Verify that the asset was actually created in the database
        result = await test_db.execute(
            select(Asset).filter(Asset.title == "Test Asset")
        )
        asset = result.scalars().first()
        assert asset is not None
        assert asset.country == "Test Country"

        # Verify that the asset feature was actually created in the database
        result = await test_db.execute(
            select(AssetFeature).filter(AssetFeature.title == "Test Feature")
        )
        feature = result.scalars().first()
        assert feature is not None
        assert feature.asset_id == created_asset.id

        # Verify that the cloud image detail was actually created in the database
        result = await test_db.execute(
            select(AssetCloudImage).filter(AssetCloudImage.public_id == "test_image_123")
        )
        image = result.scalars().first()
        assert image is not None
        assert image.asset_id == created_asset.id
    finally:
        await test_db.close()