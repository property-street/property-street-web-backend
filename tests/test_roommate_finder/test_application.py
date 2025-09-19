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
from property_street_backend.app.controllers.auth.services import fetch_access_token
from property_street_backend.tests.auth.test_user_creation import create_test_user
from property_street_backend.app.controllers.roommate_finder.models import RoommateFinder, RoomieApplication
from property_street_backend.app.controllers.roommate_finder.schemas import RoommateFinderResponseSchema
from property_street_backend.tests.activity.test_controller.test_objects import cloud_image_template

async def create_request(http_client: AsyncClient, auth_header: dict):

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

    response = await http_client.post(
        "/roommate-finder",
        json=payload,
        headers=auth_header 
    )
    assert response.status_code == 201
    response_data: RoommateFinderResponseSchema = response.json()
    assert response_data is not None
    return response_data


@pytest.mark.asyncio
async def test_application(client__fixture):
    test_db: AsyncSession = client__fixture['db'] 
    httpx_client: AsyncClient = client__fixture['http_client']

    cloud_image_detail = {
        **cloud_image_template
    }

    # create test_user and make user agent
    test_user: User = await create_test_user(test_db)
    # give the user a profile avatar
    test_user.profile_avatar = CloudImageDetail(**cloud_image_detail)
    test_db.add(test_user)
    await test_db.commit()

    # retrieve access token for requests
    token = fetch_access_token(test_user)['access_token']
    auth_header = {
        'Authorization': f'Bearer {token}',
        "Content-Type": "application/json"
    }

    roommate_finder_request: dict = await create_request(httpx_client, auth_header)
    roommate_finder_request_id=roommate_finder_request['id']
    response = await httpx_client.get(
        f'/roommate-finder/request-to-join/{roommate_finder_request_id}',
        headers=auth_header
    )    
    assert response.status_code == 201
    data = response.json()
    assert isinstance(data,list)
    assert roommate_finder_request_id in data

    query = await test_db.execute(
        select(RoomieApplication)
        .where(RoomieApplication.applicant_id == test_user.id)
    )
    result = query.scalars().all()
    recent_roomie_application: RoomieApplication = result[0]
    assert recent_roomie_application
    await test_db.delete(recent_roomie_application)
    await test_db.commit()
    await test_db.refresh(test_user)
    assert not roommate_finder_request_id in test_user.cached_roomies_application_ids