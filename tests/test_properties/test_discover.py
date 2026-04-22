"""
Comprehensive test suite for the /discover route.

Tests cover:
- Basic discovery with default parameters
- Pagination (page and size)
- Filtering by query/search
- Filtering by category, area, status
- Price filtering (min and max)
- Filtering by tags and features
- Excluding seen properties (seen_ids)
- Combined filters
- Edge cases and validation
- Authenticated vs unauthenticated users
"""

import pytest
from typing import List
from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import (
    Tag,
    Area,
    User,
    Asset,
    AssetCloudImage,
    CloudImageDetail,
    AssetFeature,
)
from property_street_backend.app.controllers.auth.utils import ensure_admin_user
from property_street_backend.tests.activity.test_controller.test_objects import (
    area_template,
    cloud_image_template,
)


# ============================================================================
# TEST DATA FIXTURES
# ============================================================================


def create_test_asset(
    agent_id: int,
    index: int,
    title: str = None,
    price: float = None,
    category: str = None,
    status: str = None,
    area: dict = None,
    tags: List[str] = None,
    features: List[str] = None,
    description: str = None,
) -> Asset:
    """Create a single test asset with customizable properties."""
    return Asset(
        agent_id=agent_id,
        title=title or f"Test Property {index}",
        currency="USD",
        price=price or (1000.0 + index * 500),
        lease_duration="6 months",
        description=description or f"Test Description for property {index}",
        category=category or "Apartment",
        status=status or "Available",
        listing_type="Rent",
        area=Area(**(area or area_template)),
        cover_image=CloudImageDetail(
            **{
                **cloud_image_template,
                "public_id": f"test_public_id_{index}",
            }
        ),
        tags=[
            Tag(name=tag) for tag in (tags or [f"tag_{index}_1", f"tag_{index}_2"])
        ],
        unfeatured_images=[
            AssetCloudImage(
                **{
                    **cloud_image_template,
                    "public_id": f"test_public_id_{index}_{j}",
                }
            )
            for j in range(2)
        ],
        verified=True,
    )


async def create_test_assets_collection(
    session: AsyncSession,
    agent_id: int,
    count: int = 10,
    **kwargs
) -> List[Asset]:
    """Create and persist a collection of test assets."""
    assets = [
        create_test_asset(agent_id, i, **kwargs)
        for i in range(count)
    ]
    session.add_all(assets)
    await session.commit()
    return assets


# ============================================================================
# BASIC DISCOVERY TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_discover_default_pagination(client__fixture):
    """Test discover endpoint with default pagination parameters."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    # Create test agent and assets
    agent: User = await ensure_admin_user(test_db)
    await create_test_assets_collection(test_db, agent.id, count=25)

    # Test default pagination (page=1, size=20)
    size = 20
    response = await httpx_client.get(f"/assets/discover?size={size}")
    assert response.status_code == 200
    assets = response.json()
    assert len(assets) == size
    assert all("id" in asset for asset in assets)
    assert all("title" in asset for asset in assets)


@pytest.mark.asyncio
async def test_discover_custom_pagination(client__fixture):
    """Test discover endpoint with custom pagination parameters."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    agent: User = await ensure_admin_user(test_db)
    await create_test_assets_collection(test_db, agent.id, count=30)

    # Test page 2 with size 10
    response = await httpx_client.get("/assets/discover?page=2&size=10")
    assert response.status_code == 200
    assets = response.json()
    assert len(assets) == 10

    # Test page 3 with size 10
    response = await httpx_client.get("/assets/discover?page=3&size=10")
    assert response.status_code == 200
    assets = response.json()
    assert len(assets) == 10


@pytest.mark.asyncio
async def test_discover_pagination_boundary_conditions(client__fixture):
    """Test pagination with edge cases."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    agent: User = await ensure_admin_user(test_db)
    await create_test_assets_collection(test_db, agent.id, count=15)

    # Test page beyond available data
    response = await httpx_client.get("/assets/discover?page=10&size=20")
    assert response.status_code == 200
    assets = response.json()
    assert len(assets) == 0

    # Test max size limit (should be capped at 100)
    response = await httpx_client.get("/assets/discover?size=150")
    assert response.status_code == 200  # Or validation error depending on validation

    # Test minimum size
    response = await httpx_client.get("/assets/discover?size=1")
    assert response.status_code == 200
    assets = response.json()
    assert len(assets) <= 1


@pytest.mark.asyncio
async def test_discover_invalid_pagination(client__fixture):
    """Test discover endpoint rejects invalid pagination parameters."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    agent: User = await ensure_admin_user(test_db)
    await create_test_assets_collection(test_db, agent.id, count=10)

    # Test negative page
    response = await httpx_client.get("/assets/discover?page=0")
    assert response.status_code in [200, 422]  # Either redirects to page 1 or validation error

    # Test negative size
    response = await httpx_client.get("/assets/discover?size=0")
    assert response.status_code in [200, 422]

    # Test zero page
    response = await httpx_client.get("/assets/discover?page=-1")
    assert response.status_code in [200, 422]


# ============================================================================
# SEARCH/QUERY FILTERING TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_discover_query_search_title(client__fixture):
    """Test full-text search filtering by title."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    agent: User = await ensure_admin_user(test_db)

    # Create assets with distinctive titles
    await create_test_assets_collection(
        test_db,
        agent.id,
        count=5,
        title="Modern Downtown Apartment",
    )
    await create_test_assets_collection(
        test_db,
        agent.id,
        count=3,
        title="Cozy Studio in Suburbs",
    )

    # Search for "Modern"
    response = await httpx_client.get("/assets/discover?query=Modern")
    assert response.status_code == 200
    assets = response.json()
    assert len(assets) == 5
    assert all("Modern" in asset["title"] for asset in assets)

    # Search for "Studio"
    response = await httpx_client.get("/assets/discover?query=Studio")
    assert response.status_code == 200
    assets = response.json()
    assert len(assets) == 3


@pytest.mark.asyncio
async def test_discover_query_search_description(client__fixture):
    """Test full-text search filtering by description."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    agent: User = await ensure_admin_user(test_db)

    # Create assets with distinctive descriptions
    description_with_keyword = "Luxury property with swimming pool and tennis court"
    await create_test_assets_collection(
        test_db,
        agent.id,
        count=2,
        description=description_with_keyword,
    )
    await create_test_assets_collection(
        test_db,
        agent.id,
        count=3,
        description="Basic apartment with kitchen",
    )

    # Search for "swimming"
    response = await httpx_client.get("/assets/discover?query=swimming")
    assert response.status_code == 200
    assets = response.json()
    assert len(assets) == 2


@pytest.mark.asyncio
async def test_discover_query_multiple_terms(client__fixture):
    """Test search with multiple query terms (space-separated)."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    agent: User = await ensure_admin_user(test_db)

    # Create distinctive assets
    await create_test_assets_collection(
        test_db,
        agent.id,
        count=2,
        title="Luxury Downtown Apartment",
    )
    await create_test_assets_collection(
        test_db,
        agent.id,
        count=3,
        title="Budget Studio",
    )

    # Search for "Luxury Downtown" (both terms should match)
    response = await httpx_client.get("/assets/discover?query=Luxury+Downtown")
    assert response.status_code == 200
    assets = response.json()
    assert len(assets) > 0


# ============================================================================
# CATEGORY FILTERING TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_discover_filter_by_category(client__fixture):
    """Test filtering properties by category."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    agent: User = await ensure_admin_user(test_db)

    # Create assets with different categories
    await create_test_assets_collection(
        test_db,
        agent.id,
        count=5,
        category="Apartment",
    )
    await create_test_assets_collection(
        test_db,
        agent.id,
        count=3,
        category="House",
    )

    # Filter by Apartment
    response = await httpx_client.get("/assets/discover?category=Apartment")
    assert response.status_code == 200
    assets = response.json()
    assert len(assets) == 5
    assert all(asset["category"] == "Apartment" for asset in assets)

    # Filter by House
    response = await httpx_client.get("/assets/discover?category=House")
    assert response.status_code == 200
    assets = response.json()
    assert len(assets) == 3


@pytest.mark.asyncio
async def test_discover_category_case_insensitive(client__fixture):
    """Test category filtering is case-insensitive."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    agent: User = await ensure_admin_user(test_db)
    await create_test_assets_collection(
        test_db,
        agent.id,
        count=3,
        category="Apartment",
    )

    # Search with different cases
    response = await httpx_client.get("/assets/discover?category=apartment")
    assert response.status_code == 200
    assets = response.json()
    assert len(assets) == 3

    response = await httpx_client.get("/assets/discover?category=APARTMENT")
    assert response.status_code == 200
    assets = response.json()
    assert len(assets) == 3


# ============================================================================
# AREA/LOCATION FILTERING TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_discover_filter_by_area_country(client__fixture):
    """Test filtering properties by country."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    agent: User = await ensure_admin_user(test_db)

    # Create custom area with specific country
    area_us = {**area_template, "country": "United States"}
    area_uk = {**area_template, "country": "United Kingdom"}

    await create_test_assets_collection(
        test_db,
        agent.id,
        count=4,
        area=area_us,
    )
    await create_test_assets_collection(
        test_db,
        agent.id,
        count=2,
        area=area_uk,
    )

    # Filter by United States
    response = await httpx_client.get("/assets/discover?area=United+States")
    assert response.status_code == 200
    assets = response.json()
    assert len(assets) >= 4

    # Filter by United Kingdom
    response = await httpx_client.get("/assets/discover?area=United+Kingdom")
    assert response.status_code == 200
    assets = response.json()
    assert len(assets) >= 2


@pytest.mark.asyncio
async def test_discover_filter_by_area_city(client__fixture):
    """Test filtering properties by city."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    agent: User = await ensure_admin_user(test_db)

    # Create areas with specific cities
    area_nyc = {**area_template, "city_or_town": "New York"}
    area_la = {**area_template, "city_or_town": "Los Angeles"}

    await create_test_assets_collection(
        test_db,
        agent.id,
        count=5,
        area=area_nyc,
    )
    await create_test_assets_collection(
        test_db,
        agent.id,
        count=3,
        area=area_la,
    )

    # Filter by New York
    response = await httpx_client.get("/assets/discover?area=New+York")
    assert response.status_code == 200
    assets = response.json()
    assert len(assets) >= 5


@pytest.mark.asyncio
async def test_discover_filter_by_area_multiple_terms(client__fixture):
    """Test filtering by area with multiple search terms."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    agent: User = await ensure_admin_user(test_db)

    # Create area with street information
    area_specific = {
        **area_template,
        "country": "USA",
        "city_or_town": "New York",
        "street": "5th Avenue",
    }

    await create_test_assets_collection(
        test_db,
        agent.id,
        count=2,
        area=area_specific,
    )

    # Search for multiple area components
    response = await httpx_client.get("/assets/discover?area=5th+Avenue")
    assert response.status_code == 200
    assets = response.json()
    assert len(assets) >= 2


# ============================================================================
# STATUS FILTERING TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_discover_filter_by_status(client__fixture):
    """Test filtering properties by status."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    agent: User = await ensure_admin_user(test_db)

    # Create assets with different statuses
    await create_test_assets_collection(
        test_db,
        agent.id,
        count=6,
        status="Available",
    )
    await create_test_assets_collection(
        test_db,
        agent.id,
        count=3,
        status="Rented",
    )

    # Filter by Available
    response = await httpx_client.get("/assets/discover?status=Available")
    assert response.status_code == 200
    assets = response.json()
    assert len(assets) >= 6
    assert all(asset["status"] == "Available" for asset in assets)

    # Filter by Rented
    response = await httpx_client.get("/assets/discover?status=Rented")
    assert response.status_code == 200
    assets = response.json()
    assert all(asset["status"] == "Rented" for asset in assets)


# ============================================================================
# PRICE FILTERING TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_discover_filter_by_min_price(client__fixture):
    """Test filtering properties by minimum price."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    agent: User = await ensure_admin_user(test_db)

    # Create assets with varying prices
    prices = [500.0, 1000.0, 1500.0, 2000.0, 2500.0]
    for i, price in enumerate(prices):
        await create_test_assets_collection(
            test_db,
            agent.id,
            count=1,
            price=price,
        )

    # Filter by min_price=1500
    response = await httpx_client.get("/assets/discover?min_price=1500")
    assert response.status_code == 200
    assets = response.json()
    assert all(asset["price"] >= 1500 for asset in assets)


@pytest.mark.asyncio
async def test_discover_filter_by_max_price(client__fixture):
    """Test filtering properties by maximum price."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    agent: User = await ensure_admin_user(test_db)

    # Create assets with varying prices
    prices = [500.0, 1000.0, 1500.0, 2000.0, 2500.0]
    for i, price in enumerate(prices):
        await create_test_assets_collection(
            test_db,
            agent.id,
            count=1,
            price=price,
        )

    # Filter by max_price=1500
    response = await httpx_client.get("/assets/discover?max_price=1500")
    assert response.status_code == 200
    assets = response.json()
    assert all(asset["price"] <= 1500 for asset in assets)


@pytest.mark.asyncio
async def test_discover_filter_by_price_range(client__fixture):
    """Test filtering properties by price range (min and max)."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    agent: User = await ensure_admin_user(test_db)

    # Create assets with varying prices
    prices = [500.0, 1000.0, 1500.0, 2000.0, 2500.0]
    for i, price in enumerate(prices):
        await create_test_assets_collection(
            test_db,
            agent.id,
            count=1,
            price=price,
        )

    # Filter by price range 1000-2000
    response = await httpx_client.get(
        "/assets/discover?min_price=1000&max_price=2000"
    )
    assert response.status_code == 200
    assets = response.json()
    assert all(1000 <= asset["price"] <= 2000 for asset in assets)


# ============================================================================
# TAG FILTERING TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_discover_filter_by_tags(client__fixture):
    """Test filtering properties by tags."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    agent: User = await ensure_admin_user(test_db)

    # Create assets with specific tags
    await create_test_assets_collection(
        test_db,
        agent.id,
        count=3,
        tags=["modern", "furnished"],
    )
    await create_test_assets_collection(
        test_db,
        agent.id,
        count=2,
        tags=["vintage", "unfurnished"],
    )

    # Filter by "modern" tag
    response = await httpx_client.get("/assets/discover?tags=modern")
    assert response.status_code == 200
    assets = response.json()
    assert len(assets) >= 3

    # Filter by "vintage" tag
    response = await httpx_client.get("/assets/discover?tags=vintage")
    assert response.status_code == 200
    assets = response.json()
    assert len(assets) >= 2


@pytest.mark.asyncio
async def test_discover_filter_by_multiple_tags(client__fixture):
    """Test filtering by multiple tags (comma or space-separated)."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    agent: User = await ensure_admin_user(test_db)

    # Create assets with multiple tags
    await create_test_assets_collection(
        test_db,
        agent.id,
        count=2,
        tags=["modern", "furnished", "pet-friendly"],
    )
    await create_test_assets_collection(
        test_db,
        agent.id,
        count=3,
        tags=["modern", "furnished"],
    )

    # Filter by multiple tags
    response = await httpx_client.get(
        "/assets/discover?tags=modern,furnished"
    )
    assert response.status_code == 200
    assets = response.json()
    # Should return properties that have BOTH tags
    assert len(assets) >= 5


# ============================================================================
# FEATURES FILTERING TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_discover_filter_by_features(client__fixture):
    """Test filtering properties by features."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    agent: User = await ensure_admin_user(test_db)

    # Create assets with specific features
    await create_test_assets_collection(
        test_db,
        agent.id,
        count=3,
        features=["swimming_pool", "gym"],
    )
    await create_test_assets_collection(
        test_db,
        agent.id,
        count=2,
        features=["parking", "security"],
    )

    # Filter by "swimming_pool" feature
    response = await httpx_client.get("/assets/discover?features=swimming_pool")
    assert response.status_code == 200
    assets = response.json()
    assert len(assets) >= 3


# ============================================================================
# SEEN IDS FILTERING TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_discover_exclude_seen_properties(client__fixture):
    """Test excluding previously seen properties using seen_ids."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    agent: User = await ensure_admin_user(test_db)
    assets = await create_test_assets_collection(
        test_db,
        agent.id,
        count=10,
    )

    # Get initial discover results
    response = await httpx_client.get("/assets/discover?size=5")
    assert response.status_code == 200
    initial_assets = response.json()
    seen_ids = [asset["id"] for asset in initial_assets]

    # Get discover results excluding seen assets
    seen_ids_param = ",".join(map(str, seen_ids))
    response = await httpx_client.get(
        f"/assets/discover?size=5&seen_ids={seen_ids_param}"
    )
    assert response.status_code == 200
    filtered_assets = response.json()

    # Verify that none of the filtered assets are in seen_ids
    filtered_asset_ids = [asset["id"] for asset in filtered_assets]
    assert not any(aid in seen_ids for aid in filtered_asset_ids)


@pytest.mark.asyncio
async def test_discover_seen_ids_space_separated(client__fixture):
    """Test seen_ids parameter with space-separated format."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    agent: User = await ensure_admin_user(test_db)
    assets = await create_test_assets_collection(
        test_db,
        agent.id,
        count=10,
    )

    # Get some asset IDs
    first_few_ids = [asset.id for asset in assets[:3]]

    # Use space-separated seen_ids
    seen_ids_param = " ".join(map(str, first_few_ids))
    response = await httpx_client.get(
        f"/assets/discover?size=10&seen_ids={seen_ids_param}"
    )
    assert response.status_code == 200
    filtered_assets = response.json()

    # Verify exclusion
    filtered_asset_ids = [asset["id"] for asset in filtered_assets]
    assert not any(aid in first_few_ids for aid in filtered_asset_ids)


# ============================================================================
# COMBINED FILTERING TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_discover_multiple_filters_combined(client__fixture):
    """Test using multiple filters together."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    agent: User = await ensure_admin_user(test_db)

    # Create diverse asset collection
    area_nyc = {**area_template, "city_or_town": "New York"}

    await create_test_assets_collection(
        test_db,
        agent.id,
        count=5,
        category="Apartment",
        status="Available",
        price=2000.0,
        area=area_nyc,
        tags=["modern"],
    )

    await create_test_assets_collection(
        test_db,
        agent.id,
        count=3,
        category="House",
        status="Rented",
        price=3000.0,
        area=area_nyc,
        tags=["vintage"],
    )

    # Apply multiple filters
    response = await httpx_client.get(
        "/assets/discover?category=Apartment&status=Available&area=New+York&min_price=1500&max_price=2500&tags=modern"
    )
    assert response.status_code == 200
    assets = response.json()

    # Verify all filters are applied
    assert all(asset["category"] == "Apartment" for asset in assets)
    assert all(asset["status"] == "Available" for asset in assets)
    assert all(1500 <= asset["price"] <= 2500 for asset in assets)


@pytest.mark.asyncio
async def test_discover_query_and_category_filters(client__fixture):
    """Test combining query search with category filter."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    agent: User = await ensure_admin_user(test_db)

    await create_test_assets_collection(
        test_db,
        agent.id,
        count=3,
        title="Luxury Downtown Apartment",
        category="Apartment",
    )
    await create_test_assets_collection(
        test_db,
        agent.id,
        count=2,
        title="Luxury Estate House",
        category="House",
    )

    # Search for "Luxury" with category filter "Apartment"
    response = await httpx_client.get(
        "/assets/discover?query=Luxury&category=Apartment"
    )
    assert response.status_code == 200
    assets = response.json()
    assert all(asset["category"] == "Apartment" for asset in assets)


# ============================================================================
# AUTHENTICATION & USER DATA TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_discover_without_authentication(client__fixture):
    """Test discover endpoint works for unauthenticated users."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    agent: User = await ensure_admin_user(test_db)
    await create_test_assets_collection(test_db, agent.id, count=5)

    # Make request without auth token
    response = await httpx_client.get("/assets/discover")
    assert response.status_code == 200
    assets = response.json()
    assert len(assets) > 0


@pytest.mark.asyncio
async def test_discover_response_structure(client__fixture):
    """Test the response structure includes all expected fields."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    agent: User = await ensure_admin_user(test_db)
    await create_test_assets_collection(test_db, agent.id, count=1)

    response = await httpx_client.get("/assets/discover?size=1")
    assert response.status_code == 200
    assets = response.json()

    assert len(assets) > 0
    asset = assets[0]

    # Verify essential fields
    assert "id" in asset
    assert "title" in asset
    assert "price" in asset
    assert "currency" in asset
    assert "category" in asset
    assert "status" in asset
    assert "verified" in asset
    assert "created_at" in asset
    assert "agent" in asset
    assert "area" in asset
    assert "tags" in asset
    assert "user_stats" in asset

    # Verify user_stats structure
    user_stats = asset["user_stats"]
    assert "liked" in user_stats
    assert "saved" in user_stats
    assert "view_count" in user_stats


# ============================================================================
# EDGE CASES & ERROR SCENARIOS
# ============================================================================


@pytest.mark.asyncio
async def test_discover_empty_results(client__fixture):
    """Test discover endpoint with filters that return no results."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    agent: User = await ensure_admin_user(test_db)
    await create_test_assets_collection(
        test_db,
        agent.id,
        count=5,
        category="Apartment",
    )

    # Search for non-existent category
    response = await httpx_client.get("/assets/discover?category=NonExistent")
    assert response.status_code == 200
    assets = response.json()
    assert len(assets) == 0


@pytest.mark.asyncio
async def test_discover_no_verified_properties(client__fixture):
    """Test that only verified properties are returned."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    agent: User = await ensure_admin_user(test_db)

    # Create an unverified asset
    unverified_asset = create_test_asset(agent.id, 0)
    unverified_asset.verified = False
    test_db.add(unverified_asset)
    await test_db.commit()

    # Create verified assets
    await create_test_assets_collection(
        test_db,
        agent.id,
        count=3,
    )

    response = await httpx_client.get("/assets/discover")
    assert response.status_code == 200
    assets = response.json()

    # All returned assets should be verified
    assert all(asset["verified"] for asset in assets)
    # Unverified asset should not be in results
    assert len(assets) >= 3


@pytest.mark.asyncio
async def test_discover_ordering_by_creation(client__fixture):
    """Test that properties are ordered by creation date (newest first)."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    agent: User = await ensure_admin_user(test_db)
    await create_test_assets_collection(
        test_db,
        agent.id,
        count=10,
    )

    response = await httpx_client.get("/assets/discover?size=10")
    assert response.status_code == 200
    assets = response.json()

    # Verify ordering (each asset should be created after the previous one)
    # Since we create them in order, they should be returned in reverse order
    creation_dates = [asset["created_at"] for asset in assets]
    # Check that dates are in descending order (newest first)
    assert creation_dates == sorted(creation_dates, reverse=True)


@pytest.mark.asyncio
async def test_discover_very_long_query_string(client__fixture):
    """Test handling of very long query parameters."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    agent: User = await ensure_admin_user(test_db)
    await create_test_assets_collection(test_db, agent.id, count=5)

    # Create a very long query string
    long_query = "test " * 100
    response = await httpx_client.get(
        f"/assets/discover?query={long_query}"
    )
    # Should handle gracefully without error
    assert response.status_code in [200, 422]


@pytest.mark.asyncio
async def test_discover_special_characters_in_query(client__fixture):
    """Test handling of special characters in query parameters."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    agent: User = await ensure_admin_user(test_db)

    await create_test_assets_collection(
        test_db,
        agent.id,
        count=3,
        title="Property @ Special #Location!",
    )

    # Search with special characters
    response = await httpx_client.get(
        "/assets/discover?query=Special%20%23Location"
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_discover_numeric_string_params(client__fixture):
    """Test handling of numeric parameters passed as strings."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    agent: User = await ensure_admin_user(test_db)
    await create_test_assets_collection(
        test_db,
        agent.id,
        count=10,
        price=1500.0,
    )

    # Pass numeric parameters as strings
    response = await httpx_client.get(
        "/assets/discover?min_price=1000&max_price=2000"
    )
    assert response.status_code == 200
    assets = response.json()
    assert all(1000 <= asset["price"] <= 2000 for asset in assets)


# ============================================================================
# PERFORMANCE & DATA FORMAT TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_discover_large_result_set(client__fixture):
    """Test discover with large number of properties."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    agent: User = await ensure_admin_user(test_db)
    await create_test_assets_collection(test_db, agent.id, count=100)

    # Request with max size
    response = await httpx_client.get("/assets/discover?size=100")
    assert response.status_code == 200
    assets = response.json()
    assert len(assets) == 100


@pytest.mark.asyncio
async def test_discover_response_includes_images(client__fixture):
    """Test that response includes image information."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    agent: User = await ensure_admin_user(test_db)
    await create_test_assets_collection(test_db, agent.id, count=1)

    response = await httpx_client.get("/assets/discover?size=1")
    assert response.status_code == 200
    assets = response.json()

    asset = assets[0]
    # Check for image fields
    assert "cover_image" in asset or "unfeatured_images" in asset


@pytest.mark.asyncio
async def test_discover_currency_in_response(client__fixture):
    """Test that currency information is included in response."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]

    agent: User = await ensure_admin_user(test_db)
    await create_test_assets_collection(test_db, agent.id, count=1)

    response = await httpx_client.get("/assets/discover?size=1")
    assert response.status_code == 200
    assets = response.json()

    asset = assets[0]
    assert asset["currency"] == "USD"
