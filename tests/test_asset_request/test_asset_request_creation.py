import json
import pytest
import asyncio
import websockets
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..utils import get_user_ws_endpoint
from property_street_backend.app.initiator import logger
from property_street_backend.app.controllers.auth import fetched_access_token
from property_street_backend.tests.auth.test_user_creation import create_test_user
from property_street_backend.app.models import User, CloudImageDetail, AssetRequest

@pytest.mark.asyncio
async def test_asset_request_creation(app_subprocess, client__fixture):
    ws = None
    test_db = None
    try:
        async for fixture_obj in client__fixture:
            test_db: AsyncSession = fixture_obj['db'] 
            http_client = fixture_obj['http_client']
            break; 

        cloud_image_detail = {
            "cloud_asset_id":"dkajdlkajdlkajsdkfjasldkfj",
            "format":"jpg",
            "bytes":102400,
            "height":800,
            "public_id":f"test_image",
            "secure_url":"https://example.com/test_image.jpg",
            "width":600,
        }
        # create test_user and make user agent to enable 
        # receipt of notification on asset creation
        test_user: User = await create_test_user(test_db)
        await test_user.become_agent(test_db)

        # give the user a profile avata, first name and last name
        test_user.profile_avatar = CloudImageDetail(**cloud_image_detail)
        test_user.first_name = 'John'
        test_user.last_name = 'Doe'
        test_db.add(test_user)
        await test_db.flush() # flush to reflect change

        # retrieve access token for requests
        token = fetched_access_token(test_user)['access_token']
        auth_header = {
            'Authorization': f'Bearer {token}',
            "Content-Type": "application/json"
        }
        # construct payload
        payload = {
            'description': 'I need a 1 bedroom flat in the maldives!',
            'area': {
                'country':'Sri-lanka',
                'state_or_province': 'Mogadishu',
                'city_or_town': 'Pisque Central', 
                'street': 'No 11 Jokey street',
            }
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
                "/asset-request",
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
            assert loaded_data.get('event') == 'asset_request'
            notification_obj = loaded_data.get('data')

        async def receipt_check_group():
            async with asyncio.TaskGroup() as tg:
                tg.create_task(send_post_request())
                tg.create_task(wait_for_notification())
        
        await asyncio.wait_for(receipt_check_group(), timeout = 60)

        # assert that the data persisted in the database
        await test_db.refresh(test_user)
        asset_requests = test_user.requested_assets
        assert asset_requests is not None
        recent_request: AssetRequest = asset_requests[0]
        assert recent_request is not None
        assert recent_request.description == payload['description']
        assert recent_request.area.country == payload['area']['country']
        assert recent_request.area.state_or_province == payload['area']['state_or_province']
        assert recent_request.area.city_or_town == payload['area']['city_or_town']
        assert recent_request.area.street == payload['area']['street']

        # assert that the notification was sent
        assert notification_obj is not None
        request_data: dict = notification_obj.get('request_data')
        assert request_data.get('db_id')
        assert request_data['description'] == payload['description'] 
        assert request_data['requester_avatar'] == test_user.profile_avatar.secure_url 
        assert request_data['requester_name'] == f'{test_user.first_name} {test_user.last_name}' 
        assert request_data['area']['country'] == payload['area']['country'] 
        assert request_data['area']['state_or_province'] == payload['area']['state_or_province'] 
        assert request_data['area']['city_or_town'] == payload['area']['city_or_town'] 
        assert request_data['area']['street'] == payload['area']['street'] 
    finally:
        if test_db:
            await test_db.close()
        if ws:
            await ws.close()