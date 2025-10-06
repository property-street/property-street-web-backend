import time
import json
import pytest
import asyncio
import websockets
from httpx import AsyncClient
from sqlalchemy import select
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession


from ..utils import get_user_ws_endpoint
from property_street_backend.app.models import (
    User,
    CloudImageDetail,
)
from property_street_backend.app.initiator import logger
from property_street_backend.app.controllers.ws_init import notification_ref
from property_street_backend.tests.auth.test_user_creation import create_test_user
from property_street_backend.app.controllers.auth.services import fetch_access_token
from property_street_backend.app.controllers.notification.models import Notification
from property_street_backend.app.controllers.auth.schemas import UserRegistrationSchema
from property_street_backend.app.controllers.roommate_finder.models import RoomieApplication
from property_street_backend.app.controllers.notification import get_pending_notification_ids
from property_street_backend.tests.activity.test_controller.test_objects import cloud_image_template
from property_street_backend.app.controllers.roommate_finder.schemas import RoommateFinderResponseSchema


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
                "public_id":f"test_image_{i}_{int(time.time())}",
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

def get_headers(token):
    return {
        'Authorization': f'Bearer {token}',
        "Content-Type": "application/json"
    }

@pytest.mark.asyncio
async def test_application( app_subprocess, client__fixture):
    test_db: AsyncSession = client__fixture['db'] 
    httpx_client: AsyncClient = client__fixture['http_client']
    redis_client: Redis = client__fixture['redis_client']

    cloud_image_detail = {
        **cloud_image_template
    }

    # create test_user and make user agent
    requester: User = await create_test_user(test_db)
    # give the user a profile avatar
    requester.profile_avatar = CloudImageDetail(**cloud_image_detail)
    test_db.add(requester)
    await test_db.commit()

    # retrieve access token for requests
    requester_token = fetch_access_token(requester)['access_token']
    requester_header = get_headers(requester_token)
    roommate_finder_request: dict = await create_request(httpx_client, requester_header)
    roommate_finder_request_id=roommate_finder_request['id']
    
    # create an applicant
    applicant: User = await create_test_user(
        test_db,
        UserRegistrationSchema(
            email = 'requester',
            password='requesterpassword',
            username='requester',
            first_name='requester'
        )
    )
    applicant_token = fetch_access_token(applicant)['access_token']

    # connnect the requester's websocket client
    requester_ws = await websockets.connect(
        get_user_ws_endpoint( requester_token )
    )
    # This delay allows both websocket be fully 
    # connected and running listener tasks; especially the recipient's ws
    await asyncio.sleep(5)

    
    applicant_headers=get_headers(applicant_token)
    async def applicant_check():
        response = await httpx_client.get(
            f'/roommate-finder/request-to-join/{roommate_finder_request_id}',
            headers=applicant_headers
        )    
        assert response.status_code == 201
        data = response.json()
        assert isinstance(data,list)
        assert roommate_finder_request_id in data

        # send in another request
        response = await httpx_client.get(
            f'/roommate-finder/request-to-join/{roommate_finder_request_id}',
            headers=applicant_headers,
        )    
        assert response.status_code == 302

        # assert deletion of roommate_finder id off applicant cache after deletion of the application
        query = await test_db.execute(
            select(RoomieApplication)
            .where(RoomieApplication.applicant_id == applicant.id)
        )
        recent_roomie_application = query.scalars().first()
        assert recent_roomie_application
        await test_db.delete(recent_roomie_application)
        await test_db.commit()
        await test_db.refresh(requester)
        assert not roommate_finder_request_id in requester.cached_roomies_application_ids
    
    async def requester_notifiation_reception():
        recv_data: dict = json.loads(await asyncio.wait_for(requester_ws.recv(),timeout=60))
        assert 'event' in recv_data
        assert 'data' in recv_data
        data = recv_data['data']
        assert data['fmt_not']['ref_id'] == roommate_finder_request_id
        assert data['fmt_not']['ref_model'] == notification_ref['roommates_finder']


    async def receipt_check_group():
        async with asyncio.TaskGroup() as tg:
            tg.create_task(applicant_check())
            tg.create_task(requester_notifiation_reception())
   
    await asyncio.wait_for(receipt_check_group(), timeout = 60)


    #--* disconnect requester, send another request and assert a notification id exists in user pend_pool *--#
    await requester_ws.close()
    # give a lil time to disconnect
    await asyncio.sleep(2)
    
    assert not await get_pending_notification_ids(requester.id, redis_client)
    
    # make another request
    response = await httpx_client.get(
        f'/roommate-finder/request-to-join/{roommate_finder_request_id}',
        headers=applicant_headers
    )    
    assert response.status_code == 201
    data = response.json()
    assert isinstance(data,list)
    assert roommate_finder_request_id in data

    # check the pend pool again
    pending_notifications = await get_pending_notification_ids(requester.id, redis_client)
    assert pending_notifications
    notification = await test_db.get(Notification,pending_notifications[0])
    assert notification.fmt_not['ref_id'] == roommate_finder_request_id
    assert notification.fmt_not['ref_model'] == notification_ref['roommates_finder']