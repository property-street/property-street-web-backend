import pytest
from httpx import AsyncClient
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import User
from property_street_backend.app.controllers.roommate_finder.models import RoommateFinder
from property_street_backend.app.controllers.auth import fetched_access_token
from property_street_backend.tests.auth.test_user_creation import create_test_user
from property_street_backend.app.initiator import logger

@pytest.mark.asyncio
async def test_roommates_finder_request(client__fixture):
    async for fixture_obj in client__fixture:
        test_db: AsyncSession = fixture_obj['db'] 
        http_client: AsyncClient = fixture_obj['http_client']
        break

    # create test_user and make user agent
    test_user: User = await create_test_user(test_db)

    # retrieve access token for requests
    token = fetched_access_token(test_user)['access_token']
    auth_header = {
        'Authorization': f'Bearer {token}',
        "Content-Type": "application/json"
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
                "cloud_asset_id":f"dkajdlkajdlkajsdkfjasldkfj{i}",
                "format":"jpg",
                "bytes":102400,
                "height":800,
                "public_id":f"test_image_{i}",
                "secure_url":"https://example.com/test_image.jpg",
                "width":600,
            } for i in range(3)
        ],
        'extra_conditions': 'I need a 1 bedroom flat in the maldives!',
        'gender': 'male',
        'category': 'hotel',
    }


    response = await http_client.post(
        "/roommate-finder",
        json=payload,
        headers=auth_header 
    )
    assert response.status_code == 201

    if response.status_code == 422:
        logger.error("Validation error: %s", response.json())
        raise HTTPException( status_code=status.HTTP_422_UNPROCESSABLE_ENTITY) 

    # assert that the data persisted in the database
    await test_db.refresh(test_user)
    roommates_finder_requests = test_user.roommates_finder
    assert roommates_finder_requests is not None
    assert test_user.gender.value == payload['gender']

    recent_request: RoommateFinder = roommates_finder_requests[0]
    assert recent_request is not None
    assert recent_request.extra_conditions == payload['extra_conditions']
    assert recent_request.max_roomies == payload['max_roomies']
    assert recent_request.category == payload['category']
    assert recent_request.area.country == payload['area']['country']
    assert recent_request.area.state_or_province == payload['area']['state_or_province']
    assert recent_request.area.city_or_town == payload['area']['city_or_town']
    assert recent_request.area.street == payload['area']['street']
    assert len(recent_request.room_images) == len(payload['room_images'])