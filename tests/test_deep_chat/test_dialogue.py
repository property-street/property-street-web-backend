import time
import json
from fastapi import WebSocket
import pytest
import asyncio
import websockets
from redis.asyncio import Redis

from property_street_backend.app.controllers.auth import fetched_access_token
from property_street_backend.tests.auth.test_user_creation import create_test_user
from property_street_backend.app.schemas.auth_schemas import UserRegistrationSchema
from property_street_backend.app.initiator import get_redis
from property_street_backend.app.controllers.chat import chat_dialogue_hset_key


def get_user_ws_endpoint(user_id):
    timestamp = int(time.time())
    return  f'ws://localhost:8001/deep-chat/{user_id}?sesion_ts={timestamp}'

@pytest.mark.asyncio
async def test_dialogue(app_subprocess):

    sender_id = 3
    recipient_id = 2
    dialogue_hset_key = chat_dialogue_hset_key(sender_id, recipient_id)

    uri1 = get_user_ws_endpoint(sender_id)
    uri2 = get_user_ws_endpoint(recipient_id)

    ws1 = await websockets.connect(uri1)
    ws2 = await websockets.connect(uri2)

    try:
        message = {
            "category": "chat",
            "sender_id": sender_id,
            "recipient_id": recipient_id,
            "msg_type": "incoming_message",
            "chat_content": "Hello recipient!",
            'status': 'unsent'
        }

        await ws1.send(json.dumps(message))

        unix_timestamp_ms = None

        async def recipient_receipt_check():
            nonlocal unix_timestamp_ms
            received_data = await ws2.recv()
            loaded_received_data: dict = json.loads(received_data)

            assert loaded_received_data.get('event') == 'incoming_message'
            chat_obj = loaded_received_data.get('data')
            assert chat_obj['status'] == 'sent'
            assert "unix_timestamp_ms" in chat_obj
            unix_timestamp_ms = chat_obj['unix_timestamp_ms']

        chat_obj = None
        async def sender_receipt_check():
            nonlocal chat_obj
            received_data = await ws1.recv()
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
        await ws2.send(json.dumps(chat_obj))
        recv_data:dict = json.loads(await asyncio.wait_for(ws1.recv(), timeout = 60))
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
        async for redis_client in get_redis():
            await redis_client.delete(dialogue_hset_key)
        await ws1.close()
        await ws2.close()