import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import (
    User,
    Area,
    CloudImageDetail,
)
from property_street_backend.app.initiator import logger
from property_street_backend.app.controllers.auth.services import fetch_access_token
from property_street_backend.tests.auth.test_user_creation import create_test_user
from property_street_backend.app.controllers.roommate_finder.models import RoommateFinder
from property_street_backend.app.controllers.roommate_finder.schemas import RoommateFinderResponseSchema

@pytest.mark.asyncio
async def test_fetch_latest_requests(client__fixture):
    test_db: AsyncSession = client__fixture['db'] 
    http_client: AsyncClient = client__fixture['http_client']

    cloud_image_detail = {
        "cloud_asset_id":"dkajdlkajdlkajsdkfjasldkfj",
        "format":"jpg",
        "bytes":102400,
        "height":800,
        "public_id":f"test_image",
        "secure_url":"https://example.com/test_image.jpg",
        "width":600,
    }

    # create test_user and make user agent
    test_user: User = await create_test_user(test_db)
    # give the user a profile avatar
    test_user.profile_avatar = CloudImageDetail(**cloud_image_detail)
    test_db.add(test_user)
    await test_db.commit()

    # retrieve access token for requests
    # token = fetch_access_token(test_user)['access_token']
    # auth_header = {
    #     'Authorization': f'Bearer {token}',
    #     "Content-Type": "application/json"
    # }
    
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

    amount = 7
    requests = [
        RoommateFinder(
            area = Area(**payload['area']),
            max_roomies = payload['max_roomies'],
            extra_conditions = payload['extra_conditions'],
            category = payload['category'],
            requester_id = test_user.id,
            room_images = [
                CloudImageDetail(
                    **{
                        **entry,
                        'public_id':f"test_image_{i}{j}",
                    }
                ) for [j,entry] in enumerate(payload['room_images'])
            ]
        ) for i in range(amount)
    ]
    test_db.add_all(requests)
    await test_db.flush()


    response = await http_client.get(
        "/roommate-finder/latests",
    )
    assert response.status_code == 200
    assert len(response.json()) == amount