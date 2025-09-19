import json
import pytest
import asyncio
import websockets
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from . import message as message_template
from ..utils import get_user_ws_endpoint
from property_street_backend.app.controllers.ws_init import user_pend_pool_key, get_timestamp_milliseconds
from property_street_backend.app.controllers.chat import chat_dialogue_hset_key
from property_street_backend.tests.auth.test_user_creation import create_test_user
from property_street_backend.app.controllers.chat import get_or_create_cached_chat
from property_street_backend.app.schemas.auth_schemas import UserRegistrationSchema
from property_street_backend.app.controllers.auth.services import fetch_access_token
from property_street_backend.app.controllers.chat.utils.store import chat_exception_handler


@pytest.mark.asyncio
async def test_dispatch_pending_messages( app_subprocess, sessions_fixture ):
    async for fixture_obj in sessions_fixture:
        test_db: AsyncSession = fixture_obj['db']
        redis_client: Redis = fixture_obj['redis_client']

    sender = await create_test_user(test_db)
    recipient = await create_test_user(test_db, UserRegistrationSchema(
        username='recipient',
        email='recipient@example.com',
        password='strongpassword',
        first_name = 'recipient'
    ))

    sender_token = fetch_access_token(sender)['access_token']
    recipient_token = fetch_access_token(recipient)['access_token']

    sender_id = sender.id
    recipient_id = recipient.id

    sender_ws = await websockets.connect( 
        get_user_ws_endpoint( sender_token )
    )

    # This delay allows both websocket be fully 
    # connected and running listener tasks; especially the recipient's ws
    await asyncio.sleep(5)

    dialogue_hset_key = chat_dialogue_hset_key(sender_id, recipient_id)
    
    try:
        message = {
            **message_template,
            "sender_id": sender_id,
            "recipient_id": recipient_id,
        }

        await sender_ws.send(json.dumps(message))
        
        # let it sleep a lil
        await asyncio.sleep(3)
        
        # assert that the chat_exception_handler stored the chat in the hset
        cached_thread = await get_or_create_cached_chat(recipient_id, sender_id, redis_client)
        cached_message = list(cached_thread.values())[0]
        # and the server_timestamp_ms field is present in the modified message object
        assert "server_timestamp_ms" in cached_message
        server_timestamp_ms = cached_message['server_timestamp_ms']


        # assert that chat token was added to the user's pend pool
        pend_pool_key = user_pend_pool_key(recipient_id)
        token_list: list[str] = json.loads(await redis_client.hget(pend_pool_key, 'messages'))
        split_token = token_list[0].split(':')
        assert split_token[0] == dialogue_hset_key
        assert split_token[1] == str(server_timestamp_ms)
        
        # connect the recipient after sending the message
        recipient_ws = await websockets.connect(
            get_user_ws_endpoint( recipient_token )
        )

        received_data = await asyncio.wait_for(recipient_ws.recv(), timeout = 60)
        loaded_received_data: dict = json.loads(received_data)
        event = loaded_received_data['event']
        assert event['type'] == 'pending_messages'
        chat_obj = loaded_received_data.get('data')
        assert isinstance(chat_obj,list)
        message1 = chat_obj[0]
        assert "server_timestamp_ms" in message1

        if recipient_ws:
            await recipient_ws.close()
    finally:
        if test_db:
            await test_db.close()
        if sender_ws:
            await sender_ws.close()
        if redis_client:
            await redis_client.aclose()