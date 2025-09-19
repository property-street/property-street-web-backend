import json
import pytest
import asyncio
import websockets
from sqlalchemy import select
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from ..utils import get_user_ws_endpoint
from property_street_backend.app.models import Notification, User, Agent
from property_street_backend.app.controllers.auth import fetched_access_token
from property_street_backend.tests.auth.test_user_creation import create_test_user
from property_street_backend.app.controllers.ws_init import (
    agent_pend_pool_key, 
    user_pend_pool_key,
    user_pend_pool_fields,
)
from property_street_backend.app.controllers.notification.utils import dispatch_pending_notification


@pytest.mark.asyncio
async def test_dispatch_pending_notification(app_subprocess, sessions_fixture):
    # Setup
    async for fixture_map in sessions_fixture:
        redis_client: Redis = fixture_map['redis_client']
        test_db: AsyncSession = fixture_map['db']
        break

    # Setup agent user
    test_user: User = await create_test_user(test_db)
    await test_user.become_agent(test_db)

    test_user_token = fetched_access_token(test_user)['access_token']
    test_notification_obj = {
        'category': 'notification',
        'description': 'bulabulabula',
        'n_status': 'undelivered',
    }

    # Notification payloads with timestamps (scores)
    zset_items = {
        json.dumps({
            **test_notification_obj,
            'description': f'bulabulabula {1000+i}',
        }): (1000 + i) for i in range(3)
    }
    await redis_client.zadd(agent_pend_pool_key, zset_items)

    #--- CASE 1: agent with NO timestamp should receive all entries ---
    async with websockets.connect( 
        get_user_ws_endpoint( test_user_token )
    ) as ws:
        loaded_response = json.loads(await asyncio.wait_for(ws.recv(), timeout = 60))
        assert loaded_response['event'] == 'agent_pending_lazy_notifications'
        assert len(loaded_response['data']) == 3

    # --- CASE 2: agent with timestamp = 1001 should get entries > 1001 ---
    async with websockets.connect( 
        get_user_ws_endpoint( test_user_token, last_n_timestamp=1000 )
    ) as ws:
        loaded_response = json.loads(await asyncio.wait_for(ws.recv(), timeout = 60))
        assert len(loaded_response['data']) == 2
    
    #--- CASE 3: agent with no timestamp but has latest notification in DB ---
    #Add one notification to DB to act as the latest
    timestamp = 1001
    notif = Notification(
        user_id=test_user.id,
        timestamp=timestamp,
    )
    test_db.add(notif)
    await test_db.commit()

    async with websockets.connect(
        get_user_ws_endpoint( test_user_token )
    ) as ws:
        loaded_response = json.loads(await asyncio.wait_for(ws.recv(), timeout = 60))
        assert len(loaded_response['data']) == 1
        assert loaded_response['data'][0]['description'] == f'bulabulabula {timestamp+1}'
 
    # --- CASE 4: regular user with notification ids in pend pool hset ---
    # for this case, remove the agent attribute of the user
    test_user.agent_profile = None
    test_db.add(test_user)

    # Create and insert two notifications
    notif1 = Notification(user_id=test_user.id, timestamp=1005, n_serialized_obj="{content: 'message'}")
    notif2 = Notification(user_id=test_user.id, timestamp=1006, n_serialized_obj="{content: 'message'}")
    test_db.add_all([notif1, notif2])
    
    # commit add added changes
    await test_db.commit()

    # Save to user pend pool
    h_key = user_pend_pool_key(test_user.id)
    await redis_client.hset(h_key, user_pend_pool_fields['notification'], json.dumps([notif1.id, notif2.id]))

    async with websockets.connect(
        get_user_ws_endpoint( test_user_token )
    ) as ws:
        loaded_response = json.loads(await asyncio.wait_for(ws.recv(), timeout = 60))
        assert len(loaded_response['data']) == 2

    # pause execution for some seconds to permit modification of notification instances
    await asyncio.sleep(5)
    await test_db.refresh(notif1)
    await test_db.refresh(notif2)
    # Ensure notifications are marked as delivered
    result = await test_db.execute(
        select(Notification).where(Notification.id.in_([notif1.id, notif2.id]))
    )
    updated = result.scalars().all()
    for n in updated:
        assert n.n_status == 'delivered'

    # Ensure Redis field is cleared
    assert not await redis_client.hget(h_key, 'notifications')