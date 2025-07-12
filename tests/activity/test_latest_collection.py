import json
import pytest
from sqlalchemy import select
from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import (
    Tag,
    Area,
    User,
    Asset, 
    Agent,
    AssetFeature, 
    AssetCloudImage,
    CloudImageDetail,
)
from property_street_backend.app.initiator import logger
from property_street_backend.tests.auth.test_create_agent import (
    create_test_agent
)
from property_street_backend.tests.activity.test_controller.test_objects import (
    area_template,
    cloud_image_template,
)
from property_street_backend.app.controllers.assets.schemas import AssetResponseSchema
from property_street_backend.app.controllers.activity import (
    auto_category_hset_key,
    newly_created_asset_set_key, 
)


@pytest.mark.asyncio
async def test_latest_collection(client__fixture):

    # Unpack the client and test database from the fixture
    async for fixture_obj in client__fixture:
        httpx_client: AsyncClient = fixture_obj['http_client'] 
        test_db: AsyncSession = fixture_obj['db']
        redis_client: Redis = fixture_obj['redis_client']
        break

    # Create a test agent/user
    created_agent: Agent = await create_test_agent(test_db)

    # Create 10 assets
    test_assets = [
        Asset(
            agent_id = created_agent.id,
            title=f"Test Asset {i}",
            currency="USD",
            price=5000.0,
            lease_duration="6 months",
            description="Test Description",
            category="Category Y",
            status="Available",
            availability="available",
            area = Area(**area_template),
            cover_image=CloudImageDetail(
                **{
                    **cloud_image_template, 
                    'public_id':f"test_public_id{i}"
                }
            ),
            tags=[
                Tag(
                    name=f"tag {i}{j}"
                ) for j in range(2)
            ],
            cloud_images=[
                AssetCloudImage(
                    **{
                        **cloud_image_template, 
                        'public_id':f"test_public_id{i}{j}"
                    }
                )
                for j in range(2)
            ],
        ) for i in range(10)
    ]
    assert len(test_assets) == 10

    # Save the last 5 asset to the database
    test_db.add_all(test_assets[:5])
    await test_db.commit()

    # Loop through the first five, 
    # add an id, has_features attribute
    # and validate em against the Schema class
    # and save to the cache
    assets_to_cache = {}
    for asset in test_assets[5:]:
        test_db.add(asset)
        await test_db.flush()
        await test_db.refresh(asset)

        stmt = (
            select(Asset)
            .options(
                selectinload(Asset.features),
                selectinload(Asset.tags),
                selectinload(Asset.area),
                selectinload(Asset.cloud_images),
                selectinload(Asset.agent)
                .selectinload(Agent.user)
                .selectinload(User.profile_avatar)
            )  # Eager load relationships
            .where(Asset.id == asset.id)
        )
        result = await test_db.execute(stmt)
        queried_asset = result.scalars().first()
        if not queried_asset:
            raise Exception(message="Queried asset not unavailable") 
        
        schematized_asset = AssetResponseSchema.model_validate(queried_asset)
        schematized_asset_dict = schematized_asset.model_dump()
        assets_to_cache[schematized_asset_dict['id']] = schematized_asset_dict
    await redis_client.hset(
        auto_category_hset_key, 
        newly_created_asset_set_key, 
        json.dumps(assets_to_cache)
    )

    # Perform the GET request with authentication
    size = 10
    response = await httpx_client.get(f"/assets/latest?size={size}")
    assert response.status_code == 200

    # Validate response structure for authenticated user
    data = response.json()
    logger.info(data)
    assert len(data['assets']) == size