import json
import asyncio
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
from property_street_backend.config.settings import ADMIN_EMAIL
from property_street_backend.tests.auth.test_create_agent import (
    create_test_agent
)
from property_street_backend.app.controllers.activity import (
    auto_category_hset_key,
    newly_created_asset_set_key, 
)
from property_street_backend.tests.activity.test_controller.test_objects import (
    area_template,
    cloud_image_template,
)
from property_street_backend.app.controllers.assets.services import eager_asset_load
from property_street_backend.app.controllers.assets.schemas import AssetResponseSchema
from property_street_backend.tests.test_properties.test_processing import property_payload
from property_street_backend.app.controllers.assets.relationship_handler import apply_model


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
    httpx_client: AsyncClient = client__fixture['http_client'] 
    test_db: AsyncSession = client__fixture['db']
    redis_client: Redis = client__fixture['redis_client']

    # Create a test agent, give it a more prioritize email
    created_agent: User = await create_test_agent(test_db)
    created_agent.email = ADMIN_EMAIL
    test_db.add(created_agent)
    await test_db.commit()
    await test_db.refresh(created_agent)

    # Create 10 assets
    test_properties = []
    for _ in range(10):
        payload = property_payload(created_agent.id)
        inst = await apply_model(Asset, test_db, payload)
        assert inst is not None
        test_properties.append(inst)
        await asyncio.sleep(1)

    # Loop through the first five, save to the cache
    # properties_to_cache = {}
    # for property in test_properties[:5]:
    #     dumped_property = AssetResponseSchema.model_validate(property).model_dump()
    #     properties_to_cache[dumped_property['id']] = dumped_property
    # 
    # await redis_client.hset(
    #     auto_category_hset_key, 
    #     newly_created_asset_set_key, 
    #     json.dumps(properties_to_cache)
    # )

    # Verify the last five, an persist
    verified_properties = []
    for property in test_properties[5:]:
        property.verified = True
        verified_properties.append(property)
    test_db.add_all(verified_properties)
    await test_db.commit()

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
                **cloud_image_template,
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


    response = await httpx_client.get(
        f"/activity/latest-collection",
        headers = { "Authorization": "Bearer " } 
    )
    assert response.status_code == 200
    response_json = response.json()
    properties = response_json['properties']
    assert len(properties['latests']) == 5
    assert len(properties['all']) == 5
    assert len(response_json['roommates_finder']['requests']) == roommates_request_size