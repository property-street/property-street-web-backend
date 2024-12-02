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

@pytest.mark.asyncio
async def test_fetch_asset_by_id(client__fixture_with_onlyDB_fixture: tuple):
    """
    Test the /activity/assets/{asset_id} endpoint to ensure it fetches
    a single asset by its ID with the correct structure.
    Covers cases where the requester is authenticated and not authenticated.
    """
    # Unpack the client and test database from the fixture
    client_gen = client__fixture_with_onlyDB_fixture
    client, test_db = await client_gen.__anext__()

    # Common cloud image details
    test_cloud_details = {
        "cloud_asset_id": "cloud_asset_id",
        "format": "format",
        "bytes": 1500,
        "height": 1620,
        "secure_url": "https://example.com/silly.png",
        "width": 1480,
    }

    # Create a single test asset with features
    test_asset = Asset(
        title="Test Asset",
        country="Country Y",
        address="Test Address",
        currency="USD",
        amount=5000.0,
        lease_duration="6 months",
        description="Test Description",
        category="Category Y",
        status="Available",
        availability=True,
        has_features=True,
        cover_image=CloudImageDetail(**test_cloud_details, public_id="test_public_id"),
        tags=[Tag(name=f"tag {i}") for i in range(2)],
        features=[
            AssetFeature(
                title=f"Asset feature {i}",
                cloud_images=[
                    AssetCloudImage(**test_cloud_details, public_id=f"test_public_id{i}{j}")
                    for j in range(2)
                ],
            )
            for i in range(2)
        ],
    )

    # Save the asset to the database
    test_db.add(test_asset)
    await test_db.commit()
    await test_db.refresh(test_asset)

    # Create a test agent and user
    test_agent = await create_test_agent(db=test_db)
    test_user = test_agent.user

    # Fetch a token for the user
    token_obj = fetched_access_token(user=test_user)
    token = token_obj["access_token"]
    headers_authenticated = {"Authorization": f"Bearer {token}"}

    # Perform the GET request with authentication
    response = await client.get(f"/activity/assets/{test_asset.id}", headers=headers_authenticated)

    # Validate response status
    assert response.status_code == 200

    # Validate response structure for authenticated user
    data = response.json()
    assert data.get('asset') is not None
    assert data.get('first_name') == test_user.first_name
    assert data.get('client_is_agent')
    assert data.get('is_authenticated') is True

    # Validate the structure of the asset
    asset = data.get('asset')
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
    assert all(key in asset for key in required_keys)

    # Perform the GET request without authentication
    headers_unauthenticated = {"Authorization": "Bearer"}
    response = await client.get(f"/activity/assets/{test_asset.id}", headers=headers_unauthenticated)

    # Validate response status
    assert response.status_code == 200

    # Validate response structure for unauthenticated user
    data = response.json()
    assert data.get('asset') is not None
    assert data.get('first_name') is None
    assert data.get('client_is_agent') is None
    assert data.get('is_authenticated') is False

    # Validate the structure of the asset
    asset = data.get('asset')
    assert all(key in asset for key in required_keys)

    # Test for a non-existent asset ID
    non_existent_asset_id = test_asset.id + 999
    response = await client.get(f"/activity/assets/{non_existent_asset_id}", headers=headers_authenticated)
    assert response.status_code == 404
    assert response.json().get('detail') == f"Asset with ID {non_existent_asset_id} not found"
