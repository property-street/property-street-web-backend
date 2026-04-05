import pytest
from typing import List
from datetime import datetime, timezone
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
)
from property_street_backend.app.controllers.auth.utils import ensure_admin_user
from property_street_backend.tests.activity.test_controller.test_objects import (
    area_template,
    cloud_image_template,
)
from property_street_backend.app.controllers.assets.asset_routine_methods import (
    newly_created_asset_zset_key,
)

def pre_commit_test_asset_collection(agent_id: int ,size: int = 10) -> List[Asset]: 
    # Create 10 assets
    return [
        Asset(
            agent_id = agent_id,
            title=f"Test Asset {i}",
            currency="USD",
            price=5000.0,
            lease_duration="6 months",
            description="Test Description",
            category="Category Y",
            status="Available",
            listing_type="Rent",
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
            unfeatured_images=[
                AssetCloudImage(
                    **{
                        **cloud_image_template, 
                        'public_id':f"test_public_id{i}{j}"
                    }
                )
                for j in range(2)
            ],
            verified=True
        ) for i in range(size)
    ]





@pytest.mark.asyncio
async def test_latest_collection(client__fixture):

    # Unpack the client and test database from the fixture
    httpx_client: AsyncClient = client__fixture['http_client'] 
    test_db: AsyncSession = client__fixture['db']
    redis_client: Redis = client__fixture['redis_client']

    # Make the agent an admin to by pass the 5-property limit
    created_agent: User = await ensure_admin_user(test_db)

    # Create 10 assets
    test_assets = pre_commit_test_asset_collection(created_agent.id)

    # Save the last 5 asset to the database
    test_db.add_all(test_assets[:5])
    await test_db.commit()

    # Loop through the next 5, add to DB, and cache their IDs
    for asset in test_assets[5:]:
        test_db.add(asset)
        await test_db.flush()
        await test_db.refresh(asset)

        # Add asset ID to the cache (not the full property data)
        timestamp = datetime.now(timezone.utc).timestamp()
        await redis_client.zadd(
            newly_created_asset_zset_key,
            {asset.id: timestamp}
        )

    # Perform the GET request
    size = 10
    response = await httpx_client.get(f"/assets/latests?size={size}")
    assert response.status_code == 200

    # Validate response structure
    assets = response.json()
    assert len(assets) == size
    assert [tag['name'] for tag in assets[0]['tags']]
    # assert for user_stats
    assert all(asset.get('user_stats') for asset in assets)