import json
import pytest
import asyncio
import websockets
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from ..utils import get_user_ws_endpoint
from property_street_backend.app.models import Notification, User, Agent
from property_street_backend.app.controllers.auth import fetched_access_token
from property_street_backend.tests.auth.test_user_creation import create_test_user
from property_street_backend.app.controllers.ws_init import agent_pend_pool_key, user_pend_pool_key
from property_street_backend.app.controllers.notification.utils import dispatch_pending_notification


@pytest.mark.asyncio
async def test_dispatch_pending_notification(app_subprocess, sessions_fixture):
    test_user_ws = None
    try:
        # Setup
        async for fixture_map in sessions_fixture:
            redis_client: Redis = fixture_map['redis_client']
            test_db: AsyncSession = fixture_map['db']
            break

        # Setup agent user
        test_user: User = await create_test_user(test_db)
        await test_user.become_agent(test_db)
        test_user_id = test_user.id

        test_user_token = fetched_access_token(test_user)['access_token']
        test_notification_obj = {
            'category': 'notification',
            'description': 'bulabulabula',
            'n_status': 'undelivered',
        }

        # Notification payloads with timestamps (scores)
        zset_items = {
            json.dumps(test_notification_obj): (1001 + i) for i in range(3)
        }
        await redis_client.zadd(agent_pend_pool_key, zset_items)

        # --- CASE 1: agent with NO timestamp should receive all entries ---
        test_user_ws = await websockets.connect( 
            get_user_ws_endpoint( test_user_token )
        )
        # await dispatch_pending_notification(
        #     last_timestamp=None,
        #     redis_client=redis_client,
        #     db=test_db,
        #     is_agent=True,
        #     user_id=test_user_id,
        #     ws=test_user_ws,
        # )
        response = await asyncio.wait_for(test_user_ws.recv(), timeout = 60)
        loaded_response = json.loads(response)
        assert loaded_response['event'] == 'agent_pending_lazy_notifications'
        assert len(loaded_response['data']) == 3

        # # --- CASE 2: agent with timestamp = 1001 should get entries > 1001 ---
        # ws2 = fake_websocket()
        # await dispatch_pending_notification(
        #     last_timestamp=1001,
        #     redis_client=redis_client,
        #     db=test_db,
        #     is_agent=True,
        #     user_id=agent_id,
        #     ws=ws2,
        # )
        # sent_2 = ws2.sent_data[-1]
        # assert len(sent_2['data']) == 2
        # assert sent_2['data'][0]['msg'] == 'not2'
    # 
        # # --- CASE 3: agent with no timestamp but has latest notification in DB ---
        # # Add one notification to DB to act as the latest
        # notif = Notification(
        #     user_id=agent_id,
        #     timestamp=1002,
        #     n_status='unsent',
        # )
        # test_db.add(notif)
        # await test_db.commit()
    # 
        # ws3 = fake_websocket()
        # await dispatch_pending_notification(
        #     last_timestamp=None,
        #     redis_client=redis_client,
        #     db=test_db,
        #     is_agent=True,
        #     user_id=agent_id,
        #     ws=ws3,
        # )
        # sent_3 = ws3.sent_data[-1]
        # assert len(sent_3['data']) == 1  # only 1003 should be left
        # assert sent_3['data'][0]['msg'] == 'not3'
    # 
        # # --- CASE 4: regular user with notification ids in pend pool hset ---
        # regular_user = await create_test_user(test_db, is_agent=False)
        # regular_id = regular_user.id
    # 
        # # Create and insert two notifications
        # notif1 = Notification(user_id=regular_id, timestamp=1005, n_status='unsent')
        # notif2 = Notification(user_id=regular_id, timestamp=1006, n_status='unsent')
        # test_db.add_all([notif1, notif2])
        # await test_db.commit()
    # 
        # # Save to user pend pool
        # h_key = user_pend_pool_key(regular_id)
        # await redis_client.hset(h_key, 'notifications', json.dumps([notif1.id, notif2.id]))
    # 
        # ws4 = fake_websocket()
        # await dispatch_pending_notification(
        #     last_timestamp=None,
        #     redis_client=redis_client,
        #     db=test_db,
        #     is_agent=False,
        #     user_id=regular_id,
        #     ws=ws4,
        # )
        # sent_4 = ws4.sent_data[-1]
        # assert sent_4['event'] == 'pending_notification'
        # assert len(sent_4['data']) == 2
    # 
        # # Ensure notifications are marked as delivered
        # result = await test_db.execute(
        #     select(Notification).where(Notification.id.in_([notif1.id, notif2.id]))
        # )
        # updated = result.scalars().all()
        # for n in updated:
        #     assert n.n_status == 'delivered'
    # 
        # # Ensure Redis field is cleared
        # remaining = await redis_client.hget(h_key, 'notifications')
        # assert remaining is None
    finally:
        if test_user_ws:
            await test_user_ws.close()