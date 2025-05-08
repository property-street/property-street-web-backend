import time
import json
import pytest
import asyncio
import websockets

from property_street_backend.app.controllers.auth import fetched_access_token
from property_street_backend.tests.auth.test_user_creation import create_test_user
from property_street_backend.app.schemas.auth_schemas import UserRegistrationSchema

def get_user_ws_endpoint(user_id):
    timestamp = int(time.time()*1000)
    return  f'ws://localhost:8001/ws/{user_id}?sesion_ts={timestamp}'

@pytest.mark.asyncio
async def test_dialogue(app_subprocess, websocket_client_fixture):
    
    # get the yield client objects
    fixture_obj = await anext(websocket_client_fixture())
    test_db = fixture_obj.get('db')
    redis_client = fixture_obj.get('redis_client')

    sender = await create_test_user(test_db)
    recipient = await create_test_user(test_db, UserRegistrationSchema(
        username='recipient',
        email='recipient@example.com',
        password='strongpassword'
    ))

    token1 = fetched_access_token(sender)['access_token']
    token2 = fetched_access_token(recipient)['access_token']
    headers1 = {'Authorization': f'Bearer {token1}'}
    headers2 = {'Authorization': f'Bearer {token2}'}

    uri1 = get_user_ws_endpoint(sender.id)
    uri2 = get_user_ws_endpoint(recipient.id)

    ws1 = await websockets.connect(uri1, extra_headers=headers1)
    ws2 = await websockets.connect(uri2, extra_headers=headers2)

    try:
        message = {
            "category": "chat",
            "recipient_id": recipient.id,
            "sender_id": sender.id,
            "msg_type": "incoming_message",
            'status': 'unsent',
            "fmt_msg_txt": "Hello recipient!",
        }

        await ws1.send(json.dumps(message))

        # Should be received by recipient
        received_data = await asyncio.wait_for(ws2.recv(), timeout=60)
        received_json = json.loads(received_data)

        assert received_json["sender_id"] == sender.id
        assert received_json["recipient_id"] == recipient.id
        assert received_json["fmt_msg_txt"] == "Hello recipient!"
        # assert "unix_timestamp_ms" in received_json
    finally:
        await ws1.close()
        await ws2.close()