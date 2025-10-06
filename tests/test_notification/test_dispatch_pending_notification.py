import time
import json
import pytest
import asyncio
import websockets
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from ..utils import get_user_ws_endpoint
from property_street_backend.app.controllers.ws_init import (
    agent_pend_pool_key, 
)
from property_street_backend.config.redis_connection_manager import get_redis
from property_street_backend.app.models import Notification, User
from property_street_backend.app.controllers.notification.utils import (
    get_pending_notification_ids,
    add_pending_notification_token_to_user_pool,
)
from property_street_backend.tests.auth.test_create_agent import create_test_agent
from property_street_backend.app.controllers.auth.services import fetch_access_token
from property_street_backend.app.controllers.ws_init import websocket_logger, pong_class
from property_street_backend.app.controllers.notification.schemas import NotificationResponse
from property_street_backend.app.controllers.notification.enums import NotificationTypeChoice


@pytest.mark.asyncio
async def test_dispatch_pending_notification(app_subprocess, sessions_fixture):
    # Setup
    redis_client: Redis = sessions_fixture['redis_client']
    test_db: AsyncSession = sessions_fixture['db']

    # Setup agent user
    test_agent: User = await create_test_agent(test_db)
    test_agent_token = fetch_access_token(test_agent)['access_token']
    fmt_not = {
        'title': 'test-notification',
        'text_content': 'A roommate application was just made',
        'media_urls': ['http://test.image','http://test.image'],
        'notification_avatar': 'http://test.image',
        'ref_model': 'roommates_finder',
        'ref_id': 3,
    }
    test_notification_obj = {
        'n_type': NotificationTypeChoice.roommate_finder.value,
        'fmt_not': fmt_not,
        'user_id': test_agent.id
    }

    not_obj_list = []
    n = 3
    for _ in range(n):
        not_obj = Notification(
            **test_notification_obj,
            timestamp=time.time()
        )
        test_db.add(not_obj)
        await test_db.flush()
        not_obj_list.append(not_obj)
        await asyncio.sleep(1)

    # Notification payloads with timestamps (scores)
    zset_items = {
        json.dumps({
            **NotificationResponse.model_validate(not_obj:= not_obj_list[i]).model_dump(),
        }): not_obj.timestamp
        for i in range(n)
    }
    scores = list(zset_items.values())
    await redis_client.zadd(agent_pend_pool_key, zset_items)
    websocket_logger.info(f'**Zset scores: {scores}')

    # === CASE 1: agent with NO timestamp should receive all entries ---
    async with websockets.connect( 
        get_user_ws_endpoint( test_agent_token )
    ) as ws:
        loaded_response = json.loads(await asyncio.wait_for(ws.recv(), timeout = 60))
        assert loaded_response['event']['class'] == pong_class['notification']
        assert len(loaded_response['data']) == n

    # === CASE 2: agent with timestamp; first timestamp from  zset items
    async with websockets.connect( 
        get_user_ws_endpoint( test_agent_token, last_n_timestamp=scores[0] )
    ) as ws:
        loaded_response = json.loads(await asyncio.wait_for(ws.recv(), timeout = 60))
        assert len(loaded_response['data'])# == (n-1)
    
    #--- CASE 3: agent with no timestamp but has latest notification in DB ---
    # Add one notification to DB to act as the latest
    await test_db.rollback() # rollback initial flush
    notif = not_obj_list[0]
    test_db.add(notif)
    await test_db.commit()

    async with websockets.connect(
        get_user_ws_endpoint( test_agent_token )
    ) as ws:
        loaded_response = json.loads(await asyncio.wait_for(ws.recv(), timeout = 60))
        assert len(loaded_response['data']) # == (n-1)
 
    # === CASE 4: regular user with notification ids in pend pool hset ---
    # for this case, remove the agent attribute of the user
    test_agent.user_role = 'user'
    test_db.add(test_agent)
    test_user = test_agent
    # Create and insert earlier 3 notifications, flush and commit changes
    test_db.add_all(not_obj_list)
    await test_db.flush()
    await test_db.commit()
    # Save to user pend pool
    user_id = test_user.id
    await add_pending_notification_token_to_user_pool(
        [inst.id for inst in not_obj_list],
        redis_client,
        user_id
    )
    async with websockets.connect(
        get_user_ws_endpoint( test_agent_token )
    ) as ws:
        loaded_response = json.loads(await asyncio.wait_for(ws.recv(), timeout = 60))
        assert len(loaded_response['data']) == n
        async with get_redis() as redis_client:
            assert not await get_pending_notification_ids(user_id, redis_client)