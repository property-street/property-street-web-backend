import time
import json
import pytest
import asyncio
import websockets

from ..utils import get_user_ws_endpoint
from property_street_backend.app.database import get_db
from property_street_backend.app.initiator import get_redis
from property_street_backend.app.controllers.auth.services import fetch_access_token
from property_street_backend.app.controllers.chat import chat_dialogue_hset_key
from property_street_backend.tests.auth.test_user_creation import create_test_user
from property_street_backend.app.schemas.auth_schemas import UserRegistrationSchema



@pytest.mark.asyncio
async def test_dialogue( app_subprocess, get_test_db__fixture ):
    test_db = await anext(get_test_db__fixture)
    sender = await create_test_user(test_db)
    recipient = await create_test_user(test_db, UserRegistrationSchema(
        username='recipient',
        email='recipient@example.com',
        password='strongpassword'
    ))

    sender_token = fetch_access_token(sender)['access_token']
    recipient_token = fetch_access_token(recipient)['access_token']

    sender_id = sender.id
    recipient_id = recipient.id
    dialogue_hset_key = chat_dialogue_hset_key(sender_id, recipient_id)

    sender_ws = await websockets.connect( 
        get_user_ws_endpoint( sender_token )
    )
    recipient_ws = await websockets.connect(
        get_user_ws_endpoint( recipient_token )
    )

    # This delay allows both websocket be fully 
    # connected and running listener tasks; especially the recipient's ws
    await asyncio.sleep(5)

    try:
        message = {
            "category": "chat",
            "sender_id": sender_id,
            "recipient_id": recipient_id,
            "msg_type": "incoming_message",
            "chat_content": "Hello recipient!",
            'status': 'unsent'
        }

        await sender_ws.send(json.dumps(message))

        unix_timestamp_ms = None

        async def recipient_receipt_check():
            nonlocal unix_timestamp_ms
            received_data = await recipient_ws.recv()
            loaded_received_data: dict = json.loads(received_data)

            assert loaded_received_data.get('event') == 'incoming_message'
            chat_obj = loaded_received_data.get('data')
            assert chat_obj['status'] == 'sent'
            assert "unix_timestamp_ms" in chat_obj
            unix_timestamp_ms = chat_obj['unix_timestamp_ms']

        chat_obj = None
        async def sender_receipt_check():
            nonlocal chat_obj
            received_data = await sender_ws.recv()
            loaded_received_data: dict = json.loads(received_data)

            assert loaded_received_data.get('event') == 'delivered_message'
            chat_data = loaded_received_data.get('data')
            assert chat_data['status'] == 'delivered'
            chat_obj = chat_data

        async def receipt_check_group():
            async with asyncio.TaskGroup() as tg:
                tg.create_task(recipient_receipt_check())
                tg.create_task(sender_receipt_check())
        
        await asyncio.wait_for(receipt_check_group(), timeout = 60)

        async for redis_client in get_redis():
            assert await redis_client.exists(dialogue_hset_key)
            assert unix_timestamp_ms
            dialogue_hset_lazy_timestamp = int(await redis_client.hget(dialogue_hset_key,'lazy_timestamp'))
            assert dialogue_hset_lazy_timestamp > 0
            dialogue_hset_chat_object:dict = json.loads(await redis_client.hget(dialogue_hset_key,'chat_object'))
            current_chat_obj = dialogue_hset_chat_object.get(str(unix_timestamp_ms))
            assert current_chat_obj['status'] == 'delivered'
            assert current_chat_obj['msg_type'] == 'delivered_message'
            break

        # modify the chat object and notify the sender
        # receive the message on the sender's socket to verify the status
        # make assertions on the chat hset to verify sync of change
        chat_obj['msg_type'] = 'read_message'
        await recipient_ws.send(json.dumps(chat_obj))
        recv_data:dict = json.loads(await asyncio.wait_for(sender_ws.recv(), timeout = 60))
        assert recv_data['event'] == 'read_message'
        mod_chat_obj = recv_data.get('data')
        assert mod_chat_obj['status'] == 'read'

        await asyncio.sleep(30)
        async for redis_client in get_redis():
            dialogue_hset_chat_object:dict = json.loads(await redis_client.hget(dialogue_hset_key,'chat_object'))
            current_chat_obj = dialogue_hset_chat_object.get(str(unix_timestamp_ms))
            assert current_chat_obj['status'] == 'read'
            assert current_chat_obj['msg_type'] == 'read_message'
            break
    finally:
        await test_db.close()
        async for redis_client in get_redis():
            await redis_client.delete(dialogue_hset_key)
        await sender_ws.close()
        await recipient_ws.close()