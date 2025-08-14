import json
import pytest
from typing import List
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
    RoommateFinder,
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
from property_street_backend.app.controllers.assets.services import eager_asset_load
from property_street_backend.app.controllers.assets.schemas import AssetResponseSchema
from property_street_backend.app.controllers.activity import (
    auto_category_hset_key,
    newly_created_asset_set_key, 
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
        ) for i in range(size)
    ]


@pytest.mark.asyncio
async def test_latest_collection(client__fixture):

    # Unpack the client and test database from the fixture
    async for fixture_obj in client__fixture:
        httpx_client: AsyncClient = fixture_obj['http_client'] 
        test_db: AsyncSession = fixture_obj['db']
        redis_client: Redis = fixture_obj['redis_client']
        break

    # Create a test agent/user
    created_agent: User = await create_test_agent(test_db)

    # Create 10 assets
    test_assets = pre_commit_test_asset_collection(created_agent.id)

    # Save the last 5 asset to the database
    test_db.add_all(test_assets[:5])

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
            eager_asset_load()
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


    cloud_image_detail = {
        "cloud_asset_id":"dkajdlkajdlkajsdkfjasldkfj",
        "format":"jpg",
        "bytes":102400,
        "height":800,
        "public_id":f"test_image",
        "secure_url":"https://example.com/test_image.jpg",
        "width":600,
    }
    # construct payload
    payload = {
        'area': {
            'country':'Sri-lanka',
            'state_or_province': 'Mogadishu',
            'city_or_town': 'Pisque Central', 
            'street': 'No 11 Jokey street',
        },
        'max_roomies': 4,
        'room_images': [
            {
                **cloud_image_detail,
                "cloud_asset_id":f"dkajdlkajdlkajsdkfjasldkfj{i}",
                "public_id":f"test_image_{i}",
            } for i in range(3)
        ],
        'extra_conditions': 'I need a 1 bedroom flat in the maldives!',
        'gender': 'male',
        'category': 'hotel',
    }

    roommates_request_size = 5
    requests = [
        RoommateFinder(
            area = Area(**payload['area']),
            max_roomies = payload['max_roomies'],
            extra_conditions = payload['extra_conditions'],
            category = payload['category'],
            requester_id = created_agent.id,
            room_images = [
                CloudImageDetail(
                    **{
                        **entry,
                        'public_id':f"test_image_{i}{j}",
                    }
                ) for [j,entry] in enumerate(payload['room_images'])
            ]
        ) for i in range(roommates_request_size)
    ]
    test_db.add_all(requests)
    await test_db.flush()


    response = await httpx_client.get(f"/activity/latest-collection")
    assert response.status_code == 200
    response_json = response.json()
    assert len(response_json['properties']) == 10
    assert len(response_json['roommates_requests']) == roommates_request_size