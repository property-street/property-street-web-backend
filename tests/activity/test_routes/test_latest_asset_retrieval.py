import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import (
    Tag,
    Asset, 
    AssetFeature, 
    AssetCloudImage,
    CloudImageDetail,
)
from property_street_backend.app.controllers.auth.services import fetch_access_token
from property_street_backend.tests.test_properties.test_processing import property_payload
from property_street_backend.app.controllers.assets.relationship_handler import apply_model
from property_street_backend.tests.auth.test_create_agent import create_test_agent, UserRegistrationSchema


@pytest.mark.asyncio
async def test_latest_assets_retrieval(client__fixture):
    """
    Test the /activity/assets/latest endpoint to ensure it fetches
    up to 100 latest assets with the correct structure.
    """
    # Extract the fixture object
    test_db: AsyncSession = client__fixture["db"]
    client: AsyncClient = client__fixture["http_client"]


    # Create a test agent and user
    test_agent = await create_test_agent(db=test_db)

    assets = []
    # Create test assets with features
    for _ in range(10):
        payload = property_payload(test_agent.id)
        inst = await apply_model(Asset, test_db, payload)
        assert inst is not None
        assets.append(inst)
        await asyncio.sleep(1)

    # Save assets to the database
    test_db.add_all(assets)
    await test_db.commit()


    # Fetch a token for the user
    token = fetch_access_token(user = test_agent)["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Perform the GET request to fetch the latest assets
    # Validate response status
    response = await client.get("/activity/assets/latest", headers=headers)
    assert response.status_code == 200
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
    assert all((key in asset) for key in required_keys for asset in assets)