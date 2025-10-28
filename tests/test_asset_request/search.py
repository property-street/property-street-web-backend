import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.controllers.asset_request.search import (
    Area,
    AssetRequest,
    search_asset_requests,
)
from property_street_backend.tests.auth.test_user_creation import create_test_user
from property_street_backend.app.controllers.asset_request.schemas import AssetRequestResponseSchema


@pytest.mark.asyncio
async def test_search_asset_requests(client__fixture):
    # Fetch DB session
    test_db: AsyncSession = client__fixture['db']

    test_user = await create_test_user(test_db)
    
    # Step 1: Create area
    area = Area(
        country="Nigeria",
        state_or_province="Abuja",
        city_or_town="Garki",
        street="Adetokunbo Ademola",
        zip_or_postal_code="900001"
    )
    test_db.add(area)
    await test_db.commit()
    await test_db.refresh(area)

    # Step 2: Create asset requests
    requests = [
        AssetRequest(
            description="Looking for a family apartment near the central area.",
            area_id=area.id,
            requester_id = test_user.id
        ),
        AssetRequest(
            description="Interested in small land for development of flats.",
            area_id=area.id,
            requester_id = test_user.id
        )
    ]
    test_db.add_all(requests)
    await test_db.commit()

    # Step 3: Perform search
    query_data = {
        "keywords": ["Garki", "family", "flat"],
        "numbers": [500000]
    }
    results = await search_asset_requests(query_data, test_db)

    # Step 4: Assertions
    assert isinstance(results, list)
    assert len(results) > 0
    assert any("family" in r["data"]['description'] for r in results)
    assert all("Garki" in r["data"]['area']['city_or_town'] for r in results)
    assert all(r["type"] == "property-request" for r in results)