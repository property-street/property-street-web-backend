import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.controllers.assets.models import (
    Asset,
    AssetFeature,
    AssetCloudImage,
)
from property_street_backend.app.models import Area, Tag, CloudImageDetail
from property_street_backend.app.controllers.assets.search import search_assets  # adjust import path
from property_street_backend.tests.auth.test_create_agent import create_test_agent
from property_street_backend.app.controllers.assets.schemas import AssetResponseSchema 
from property_street_backend.tests.activity.test_controller.test_objects import cloud_image_template

@pytest.mark.asyncio
async def test_search_assets_basic(client__fixture):
    """
    Tests search_assets() for keyword and numeric matching.
    """
    # fetch the async db session from fixture
    test_db: AsyncSession = client__fixture['db']
    httpx_client: AsyncClient = client__fixture['http_client']

    test_agent = await create_test_agent(test_db)

    # -----------------------------
    # 1. Prepare supporting data
    # -----------------------------

    tag = Tag(name="Luxury")

    asset1 = Asset(
        title="Beautiful Apartment in Ikeja",
        currency="NGN",
        price=850000,
        lease_duration="1 year",
        description="Spacious 2-bedroom flat with swimming pool",
        category="Apartment",
        status="sold",
        listing_type="rent",
        area=Area(
            country="Nigeria",
            state_or_province="Lagos",
            city_or_town="Ikeja",
            street="Allen Avenue",
        ),
        tags=[tag],
        agent_id = test_agent.id,
        cover_image = CloudImageDetail(
            **{
                **cloud_image_template,
                "public_id":"id1"
            }
        ),
        features = [
            AssetFeature(
                title="feature_title",
                cloud_images = [
                    AssetCloudImage(
                        **{
                            **cloud_image_template,
                            "public_id" : "id2"
                        },
                    )
                ]
            )
        ],
        verified=True
    )

    asset2 = Asset(
        title="Affordable Mini Flat in Yaba",
        currency="NGN",
        price=400000,
        lease_duration="1 year",
        description="1-bedroom mini flat close to Unilag",
        category="Mini Flat",
        status="available",
        listing_type="sale",
        area=Area(
            country="Nigeria",
            state_or_province="Lagos",
            city_or_town="Yaba",
            street="Herbert Macaulay Way",
        ),
        tags=[],
        agent_id = test_agent.id,
        cover_image = CloudImageDetail(
            **{
                **cloud_image_template,
                "public_id":"id3"
            }
        ),
        unfeatured_images = [
            AssetCloudImage(
                **{
                    **cloud_image_template,
                    "public_id" : f"id4{i}"
                },
            ) for i in range(2)
        ],
        verified=True
    )

    tag3 = Tag(name="Self contain")
    asset3 = Asset(
        title="1 Bedroom Apartment to Let",
        currency="NGN",
        price=400000,
        lease_duration="1 year",
        description="Band A || Secured environment || interlocked compound || good water supply",
        category="Self contain",
        status="available",
        listing_type="sale",
        area=Area(
            country="Nigeria",
            state_or_province="Rivers",
            city_or_town="Port Harcout",
            street="Rumukwurushi new layout",
        ),
        tags=[tag3],
        agent_id = test_agent.id,
        cover_image = CloudImageDetail(
            **{
                **cloud_image_template,
                "public_id":"id5"
            }
        ),
        unfeatured_images = [
            AssetCloudImage(
                **{
                    **cloud_image_template,
                    "public_id" : f"id6{i}"
                },
            ) for i in range(2)
        ],
        verified=True
    )

    test_db.add_all([asset1, asset2, asset3])
    await test_db.commit()

    search = "mini flat apartment in ikeja at $800000"
    response = await httpx_client.get(f'/search/{search}/')
    assert response.status_code == 200
    results = response.json()
    print("Mini flats search result: ", results)

    # Test Ikeja search
    assert any("Ikeja" in r["data"]['title'] for r in results)
    assert any(r["type"] == "property" for r in results)
    # Test mini flat search
    assert any("Mini" in r["data"]['title'] for r in results)
    assert any("Flat" in r["data"]['title'] for r in results)
    # Test 1 bedroom flats
    # Test price search (~800k range)
    assert any(abs(float(r["data"]['price']) - 800000) < 200000 for r in results)

    #====================================================
    # Search for 1 bedroom flat
    #====================================================
    search = "sold 1 bedroom flats"
    response = await httpx_client.get(f'/search/{search}/')
    assert response.status_code == 200
    results = response.json()
    print("1 bedroom flats search result: ",results)

    # Test Ikeja search
    assert any(r["type"] == "property" for r in results)
    assert any("1 bedroom" in r["data"]['title'].lower() for r in results)
    assert any("bedroom" in r["data"]['description'].lower() for r in results)
    assert any("sold" in r["data"]['status'].lower() for r in results)