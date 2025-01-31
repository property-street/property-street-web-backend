import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import (
    Agent, 
    Asset, 
    CloudImageDetail, 
    AssetFeature, 
    Tag,
    AssetCloudImage,
)
from property_street_backend.app.controllers.auth import (
    create_agent
)
from property_street_backend.app.schemas.auth_schemas import (
    UserRegistrationSchema
)
from property_street_backend.app.controllers.activity.agent_assets_retrieval import (
    get_agent_assets
)

async def create_asset_and_component(db, agent):
        # Create assets linked to the agent
        asset1 = Asset(
            agent_id=agent.id,
            title="Test Asset 1",
            category="Real Estate",
            country="USA",
            address="123 Main St",
            currency="USD",
            amount=500000,
            status="For Sale",
            description="Test description for asset 1",
            has_features=True,
        )
        asset2 = Asset(
            agent_id=agent.id,
            title="Test Asset 2",
            category="Vehicle",
            country="Germany",
            address="456 Main St",
            currency="EUR",
            amount=30000,
            status="For Rent",
            description="Test description for asset 2",
            has_features=False
        )
        db.add_all([asset1, asset2])
        await db.flush()  # Ensure assets have IDs

        # Create tags for assets
        tag1 = Tag(name="Luxury", assets=[asset1,])
        tag2 = Tag(name="Modern", assets=[asset1,])
        db.add_all([tag1, tag2])

        # Create a cover image for the first asset
        cover_image = CloudImageDetail(
            asset=asset1,
            cloud_asset_id="cover123",
            format="jpg",
            bytes=204800,
            height=800,
            width=600,
            public_id="cover_image_1",
            secure_url="https://example.com/cover_image.jpg"
        )
        cover_image.asset = asset1
        db.add(cover_image)
        cover_image.asset = asset2
        db.add(cover_image)

        # Create asset features for the first asset
        feature1 = AssetFeature(
            asset_id=asset1.id,
            title="Swimming Pool"
        )
        db.add(feature1)
        await db.flush()  # Ensure feature has an ID

        # Add images to the feature
        feature_image = AssetCloudImage(
            asset_feature_id=feature1.id,
            cloud_asset_id="feature_img123",
            format="png",
            bytes=102400,
            height=600,
            width=400,
            public_id="feature_image_1",
            secure_url="https://example.com/feature_image.png"
        )
        db.add(feature_image)
        
        # commit transaction to the database
        await db.commit()


@pytest.mark.asyncio
async def test_get_agent_assets(get_test_db__fixture: AsyncSession):
    try:
        # Fetch the test DB session
        test_db = await get_test_db__fixture

        # Step 1: Create test data in the database

        # Create an agent
        user_data = UserRegistrationSchema(
            email="agent@example.com",
            username="agentuser",
            password="password123"
        )

        # Call the create_agent function
        agent = await create_agent(test_db, user_data)

        # create the asset and component
        await create_asset_and_component(
            db = test_db,
            agent = agent
        )

        # Step 2: Call the function to test
        response = await get_agent_assets(test_db, agent_id=agent.id)
        assert response is not None

        # Step 3: Assertions
        print(response)
        assets_data = response['assets_data']
        assert len(assets_data) == 2  

        # Additional assertions can be added to check nested structures, tags, etc.
    finally:
        await test_db.close()