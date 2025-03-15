import pytest

from property_street_backend.app.models import (
    Tag,
    Asset, 
    AssetFeature, 
    AssetCloudImage,
    CloudImageDetail,
)
from property_street_backend.app.controllers.auth import (
    fetched_access_token,
)
from property_street_backend.tests.activity.test_controller.test_asset_creation import (
    create_test_agent
)


import pytest

@pytest.mark.asyncio
async def test_latest_assets_retrieval(client__fixture):
    # Extract the fixture object
    fixture_obj = await client__fixture.__anext__()
    test_db = fixture_obj.get("db")
    client = fixture_obj.get("http_client")
    """
    Test the /activity/assets/latest endpoint to ensure it fetches
    up to 100 latest assets with the correct structure.
    """

    # Common cloud image details
    test_cloud_details = {
        "cloud_asset_id": "cloud_asset_id",
        "format": "format",
        "bytes": 1500,
        "height": 1620,
        "secure_url": "https://example.com/silly.png",
        "width": 1480,
    }

    # Create test assets with features
    assets = [
        Asset(
            title=f"Asset {i}",
            country="Country X",
            address=f"Address {i}",
            currency="USD",
            amount=i * 1000.0,
            lease_duration="12 months",
            description=f"Description {i}",
            category="Category X",
            status="Available",
            availability="Available",
            has_features=True,
            cover_image=CloudImageDetail(**test_cloud_details, public_id=f"public_id{i}"),
            tags=[Tag(name=f"tag {i}{j}") for j in range(2)],
            features=[
                AssetFeature(
                    title=f"Asset feature {j}",
                    cloud_images=[
                        AssetCloudImage(**test_cloud_details, public_id=f"public_id{i}{j}{k}")
                        for k in range(2)
                    ],
                )
                for j in range(2)
            ],
        )
        for i in range(10)  # Create 150 assets for testing
    ]

    # Save assets to the database
    test_db.add_all(assets)
    await test_db.commit()

    # Create a test agent and user
    test_agent = await create_test_agent(db=test_db)
    test_user = test_agent.user

    # Fetch a token for the user
    token_obj = fetched_access_token(user=test_user)
    token = token_obj["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Perform the GET request to fetch the latest assets
    # Validate response status
    response = await client.get("/activity/assets/latest", headers=headers)
    assert response.status_code == 200

    # Validate response structure
    data = response.json()
    assets = data.get('assets')
    assert isinstance(assets, list)
    assert len(assets) <= 100  # Ensure only 100 assets are returned

    # Validate the structure of each asset
    required_keys = {
        "title",
        "country",
        "address",
        "currency",
        "amount",
        "lease_duration",
        "description",
        "category",
        "status",
        "availability",
        "has_features",
    }
    for asset in assets:
        assert all(key in asset for key in required_keys)

    # fetch without authentication
    headers = {"Authorization": f"Bearer "}
    response = await client.get("/activity/assets/latest", headers=headers)
    
    # Validate response status
    assert response.status_code == 200

    # Validate response structure
    data = response.json()
    assets = data.get('assets')
    assert isinstance(assets, list)
    assert len(assets) <= 100  # Ensure only 100 assets are returned

    # Validate the structure of each asset
    required_keys = {
        "title",
        "country",
        "address",
        "currency",
        "amount",
        "lease_duration",
        "description",
        "category",
        "status",
        "availability",
        "has_features",
    }
    for asset in assets:
        assert all(key in asset for key in required_keys)
