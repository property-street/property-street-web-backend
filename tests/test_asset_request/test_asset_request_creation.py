import json
import pytest
import asyncio
import websockets
from fastapi import HTTPException, status

from ..utils import get_user_ws_endpoint
from property_street_backend.app.controllers.auth import fetched_access_token
from property_street_backend.tests.auth.test_user_creation import create_test_user
from property_street_backend.app.initiator import logger

@pytest.mark.asyncio
async def test_asset_request_creation(app_subprocess, client__fixture):
    try:
        fixture_obj = await anext(client__fixture)
        test_db = fixture_obj.get('db') 
        http_client = fixture_obj.get('http_client') 

        # create test_user and make user agent
        test_user = await create_test_user(test_db)
        await test_user.become_agent(test_db)

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
        recent_request = asset_requests[0]
        assert recent_request is not None
        assert recent_request.description == payload['description']
        assert recent_request.area.country == payload['area']['country']
        assert recent_request.area.state_or_province == payload['area']['state_or_province']
        assert recent_request.area.city_or_town == payload['area']['city_or_town']
        assert recent_request.area.street == payload['area']['street']

        # assert that the notification was sent
        assert notification_obj is not None
        assert notification_obj.get('db_id')
        request_data = notification_obj.get('request_data')
        assert request_data['description'] == payload['description'] 
        assert request_data['area']['country'] == payload['area']['country'] 
        assert request_data['area']['state_or_province'] == payload['area']['state_or_province'] 
        assert request_data['area']['city_or_town'] == payload['area']['city_or_town'] 
        assert request_data['area']['street'] == payload['area']['street'] 
    finally:
        await test_db.close()
        await ws.close()