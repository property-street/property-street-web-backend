import pytest
from datetime import datetime

from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from property_street_backend.app.models import (
    Asset, 
    AssetFeature, 
    CloudImageDetail,
    Agent,
)
from property_street_backend.app.schemas.asset_schemas import (
    AssetCreateSchema, 
    AssetFeatureCreateSchema, 
    CloudImageDetailCreateSchema,
)
from property_street_backend.app.schemas.auth_schemas import (
    AgentRegistrationSchema, 
)
from property_street_backend.app.controllers.auth import get_password_hash

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
        agent_id=asset_data.agent_id
    )
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


async def create_cloud_image_detail(db: AsyncSession, image_data: CloudImageDetailCreateSchema):
    new_image = CloudImageDetail(
        created_at=datetime.fromisoformat(image_data.created_at),
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


async def create_agent(db: AsyncSession, agent_data: AgentRegistrationSchema):
    hashed_password = get_password_hash(agent_data.password)
    
    agent = Agent(
        email= agent_data.email,
        username= agent_data.username,
        password= hashed_password
    )

    db.add(agent)
    await db.commit()  
    await db.refresh(agent)  
    return agent


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
        availability=True,
        agent_id=agent_id  # Add agent ID if needed
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
    image_data = CloudImageDetailCreateSchema(
        created_at="2023-01-01T00:00:00Z",
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
    agent_data = AgentRegistrationSchema(
        email="agent@example.com",
        username="agentuser",
        password="password123"
    )
    return await create_agent(db, agent_data)



@pytest.mark.asyncio
async def test_controller_create_asset_feature_and_image(get_test_db__fixture: AsyncSession):
    
    # Fetch the test DB session
    test_db = await get_test_db__fixture

    # Create a test agent/user
    created_agent = await create_agent(test_db)
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
        select(CloudImageDetail).filter(CloudImageDetail.public_id == "test_image_123")
    )
    image = result.scalars().first()
    assert image is not None
    assert image.asset_id == created_asset.id