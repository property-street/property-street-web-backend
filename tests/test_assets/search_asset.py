import pytest
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
    try:
        # fetch the async db session from fixture
        test_db: AsyncSession = client__fixture['db']

        test_agent = await create_test_agent(test_db)

        # -----------------------------
        # 1. Prepare supporting data
        # -----------------------------
        area = Area(
            country="Nigeria",
            state_or_province="Lagos",
            city_or_town="Ikeja",
            street="Allen Avenue",
        )

        tag = Tag(name="Luxury")

        asset1 = Asset(
            title="Beautiful Apartment in Ikeja",
            description="Spacious 2-bedroom flat with swimming pool",
            category="Apartment",
            currency="NGN",
            status="available",
            price=850000,
            lease_duration="1 year",
            area=area,
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
            ]
        )

        asset2 = Asset(
            title="Affordable Mini Flat in Yaba",
            description="1-bedroom mini flat close to Unilag",
            category="Mini Flat",
            currency="NGN",
            status="available",
            price=400000,
            lease_duration="1 year",
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
            cloud_images = [
                AssetCloudImage(
                    **{
                        **cloud_image_template,
                        "public_id" : f"id4{i}"
                    },
                ) for i in range(2)
            ]
        )

        test_db.add_all([asset1, asset2])
        await test_db.commit()

        # -----------------------------
        # 2. Define queries to test
        # -----------------------------
        # match by location
        query1 = {"keywords": ["ikeja"], "numbers": []}
        # match by category/description
        query2 = {"keywords": ["mini", "flat"], "numbers": []}
        # match by numeric price proximity
        query3 = {"keywords": [], "numbers": [800000]}

        # -----------------------------
        # 3. Run the search
        # -----------------------------
        results_ikeja = await search_assets(query1, test_db)
        results_mini_flat = await search_assets(query2, test_db)
        results_price = await search_assets(query3, test_db)

        # -----------------------------
        # 4. Validate results
        # -----------------------------
        # Test Ikeja search
        assert any("Ikeja" in r["data"].title for r in results_ikeja)
        assert all(r["type"] == "asset" for r in results_ikeja)

        # Test mini flat search
        assert any("Mini" in r["data"].title for r in results_mini_flat)
        assert any("Flat" in r["data"].title for r in results_mini_flat)

        # Test price search (~800k range)
        assert any(abs(float(r["data"].price) - 800000) < 200000 for r in results_price)

        # Schema validation (optional)
        for res in results_ikeja:
            validated = AssetResponseSchema.model_validate(res["data"])
            assert validated.title

    finally:
        await test_db.close()
