import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import (
    User,
    CloudImageDetail,
)
from property_street_backend.app.initiator import logger
from property_street_backend.app.controllers.auth import fetched_access_token
from property_street_backend.tests.auth.test_user_creation import create_test_user
from property_street_backend.app.controllers.roommate_finder.models import RoommateFinder
from property_street_backend.app.controllers.roommate_finder.schemas import RoommateFinderResponseSchema

@pytest.mark.asyncio
async def test_roommates_finder_request(client__fixture):
    async for fixture_obj in client__fixture:
        test_db: AsyncSession = fixture_obj['db'] 
        http_client: AsyncClient = fixture_obj['http_client']
        break

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
                **cloud_image_detail,
                "cloud_asset_id":f"dkajdlkajdlkajsdkfjasldkfj{i}",
                "public_id":f"test_image_{i}",
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
    response_data: RoommateFinderResponseSchema = response.json()
    assert response_data is not None

    if response.status_code == 422:
        logger.error("Validation error: %s", response_data)
        raise HTTPException( status_code=status.HTTP_422_UNPROCESSABLE_ENTITY) 

    # assert test user attributes
    await test_db.refresh(test_user)
    roommates_finder_requests = test_user.roommates_finder
    assert roommates_finder_requests is not None
    assert test_user.gender.value == payload['gender']

    schematized_response = RoommateFinderResponseSchema.model_validate(response_data)
    assert schematized_response.extra_conditions == payload['extra_conditions']
    assert schematized_response.max_roomies == payload['max_roomies']
    assert schematized_response.category == payload['category']
    assert schematized_response.area.country == payload['area']['country']
    assert schematized_response.area.state_or_province == payload['area']['state_or_province']
    assert schematized_response.area.city_or_town == payload['area']['city_or_town']
    assert schematized_response.area.street == payload['area']['street']
    assert len(schematized_response.room_images) == len(payload['room_images'])
    assert schematized_response.requester == f"{test_user.first_name} {test_user.last_name}"
    assert schematized_response.requester_avatar_url == test_user.profile_avatar.secure_url
    assert schematized_response.gender == payload['gender']