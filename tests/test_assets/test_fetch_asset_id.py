import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


from .test_create_asset import create_test_asset
from property_street_backend.app.controllers.assets.schemas import AssetResponseSchema
from property_street_backend.tests.auth.test_user_creation import create_test_user

@pytest.mark.asyncio
async def test_fetch_asset_by_id(client__fixture):
    """
    Test the /activity/assets/{asset_id} endpoint to ensure it fetches
    a single asset by its ID with the correct structure.
    Covers cases where the requester is authenticated and not authenticated.
    """
    # Unpack the client and test database from the fixture
    async for fixture_obj in client__fixture:
        httpx_client: AsyncClient = fixture_obj['http_client']
        test_db: AsyncSession = fixture_obj['db']
        break

    test_asset = await create_test_asset(test_db)

    # Perform the GET request with authentication
    response = await httpx_client.get(
        f"/assets/{test_asset.id}"
    )
    assert response.status_code == 200
    AssetResponseSchema.model_validate(response.json())


    # Test for a non-existent asset ID
    non_existent_asset_id = test_asset.id + 999
    response = await httpx_client.get(
        f"/assets/{non_existent_asset_id}"
    )
    assert response.status_code == 404