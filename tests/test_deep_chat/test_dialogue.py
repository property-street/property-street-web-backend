import time
import json
import pytest
import asyncio
import websockets
from redis.asyncio import Redis

from property_street_backend.app.controllers.auth import fetched_access_token
from property_street_backend.tests.auth.test_user_creation import create_test_user
from property_street_backend.app.schemas.auth_schemas import UserRegistrationSchema

def get_user_ws_endpoint(user_id):
    timestamp = int(time.time())
    return  f'ws://localhost:8001/deep-chat/{user_id}?sesion_ts={timestamp}'

@pytest.mark.asyncio
async def test_dialogue(app_subprocess, websocket_client_fixture):

    async for fixture_obj in websocket_client_fixture:
        redis_client: Redis = fixture_obj.get('redis_client')
        break

    sender_id = 1
    recipient_id = 2
    dialogue_hset_key = f'chat_{min(sender_id, recipient_id)}{max(sender_id, recipient_id)}'

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

        # Should be received by recipient
        received_data = await asyncio.wait_for(ws2.recv(), timeout=60)
        loaded_received_data = json.loads(received_data)

        assert loaded_received_data.get('event') == 'incoming_message'
        chat_obj = loaded_received_data.get('data')
        assert chat_obj['status'] == 'sent'
        assert "unix_timestamp_ms" in chat_obj
        unix_timestamp_ms = chat_obj['unix_timestamp_ms']

        dialogue_exist = False
        for _ in range(20):
            if await redis_client.exists(dialogue_hset_key):
                dialogue_exist = True
                break 
            await asyncio.sleep(1)

        if dialogue_exist:
            dialogue_hset_lazy_timestamp = int(await redis_client.hget(dialogue_hset_key,'lazy_timestamp'))
            assert dialogue_hset_lazy_timestamp > 0
            dialogue_hset_chat_object = json.loads(await redis_client.hget(dialogue_hset_key,'chat_object'))
            current_chat_obj = dialogue_hset_chat_object(str(unix_timestamp_ms))
            assert current_chat_obj['status'] == 'delivered'
            assert current_chat_obj['msg_type'] == 'delivered_message'
        else:
            class DialogueDoesNotExistError(Exception):
                pass
            raise DialogueDoesNotExistError
    finally:
        await ws1.close()
        await ws2.close()