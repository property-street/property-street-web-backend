import json
import pytest
import asyncio
import websockets
from httpx import AsyncClient
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..utils import get_user_ws_endpoint
from property_street_backend.app.initiator import logger
from property_street_backend.app.models import User, CloudImageDetail
from property_street_backend.app.controllers.auth import fetched_access_token
from property_street_backend.tests.auth.test_user_creation import create_test_user
from property_street_backend.app.controllers.roommate_finder.models import RoommateFinder
from property_street_backend.app.controllers.roommate_finder.schemas import RoommateFinderResponseSchema

@pytest.mark.asyncio
async def test_roommates_finder_request(app_subprocess, client__fixture):
    try:
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
        test_user = await create_test_user(test_db)
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
            'gender': 'female',
            'max_roomies': 4,
            'room_images': [
                {
                    **cloud_image_detail,
                    "cloud_asset_id":f"dkajdlkajdlkajsdkfjasldkfj{i}",
                    "public_id":f"test_image_{i}",
                } for i in range(3)
            ],
            'extra_conditions': 'I need a 1 bedroom flat in the maldives!',
            'category': 'hotel',
        }

        # connect ws client
        uri = get_user_ws_endpoint(token)
        ws = await websockets.connect(uri)

        # ensure the client ws is fully connected and 
        # running tasks before the request is sent
        await asyncio.sleep(10)

        # function to send post request
        async def send_post_request():
            response = await http_client.post(
                "/roommate-finder",
                json=payload,
                headers=auth_header 
            )
            assert response.status_code == 201

            if response.status_code == 422:
                logger.error("Validation error: %s", response.json())
                raise HTTPException( status_code=status.HTTP_422_UNPROCESSABLE_ENTITY) 

        notification_obj:dict = None
        # function to wait for the notification object
        async def wait_for_notification():
            nonlocal notification_obj
            received_data = await ws.recv()
            loaded_data: dict = json.loads(received_data)
            assert loaded_data.get('event') == 'roommates_finder'
            notification_obj = loaded_data.get('data')

        async def receipt_check_group():
            async with asyncio.TaskGroup() as tg:
                tg.create_task(send_post_request())
                tg.create_task(wait_for_notification())
        
        await asyncio.wait_for(receipt_check_group(), timeout = 60)

        # assert the updated user
        await test_db.refresh(test_user)
        assert test_user.gender.value == payload['gender']
        roommates_finder_requests = test_user.roommates_finder
        assert roommates_finder_requests is not None
        
        # assert persistence of RoommateFinder
        recent_request: RoommateFinder = roommates_finder_requests[0]
        assert recent_request is not None
        schematized_response = RoommateFinderResponseSchema.model_validate(recent_request)
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

        # assert that the notification was sent
        assert notification_obj is not None
        roomies_request_data: dict = notification_obj.get('request_data')
        assert roomies_request_data is not None
        assert roomies_request_data.get('db_id')
        assert roomies_request_data['gender'] == payload['gender']
        assert roomies_request_data['category'] == payload['category']
        assert roomies_request_data['extra_conditions'] == payload['extra_conditions']
        assert roomies_request_data['max_roomies'] == payload['max_roomies']
        assert roomies_request_data['area']['country'] == payload['area']['country']
        assert roomies_request_data['area']['state_or_province'] == payload['area']['state_or_province']
        assert roomies_request_data['area']['city_or_town'] == payload['area']['city_or_town']
        assert roomies_request_data['area']['street'] == payload['area']['street']
        assert len(roomies_request_data['room_images']) == len(payload['room_images'])
        assert roomies_request_data['requester_avatar'] == test_user.profile_avatar.secure_url
    finally:
        await test_db.close()
        await ws.close()