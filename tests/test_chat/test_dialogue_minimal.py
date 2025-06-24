import json
import time
import pytest
import asyncio
import websockets
from sqlalchemy.ext.asyncio import AsyncSession

from ..utils import get_user_ws_endpoint
from property_street_backend.app.controllers.auth import fetched_access_token
from property_street_backend.tests.auth.test_user_creation import create_test_user
from property_street_backend.app.schemas.auth_schemas import UserRegistrationSchema


@pytest.mark.asyncio
async def test_dialogue(app_subprocess, get_test_db__fixture):
    
    # get the yield client objects
    test_db: AsyncSession = await anext(get_test_db__fixture)

    sender = await create_test_user(test_db)
    recipient = await create_test_user(test_db, UserRegistrationSchema(
        username='recipient',
        email='recipient@example.com',
        password='strongpassword'
    ))
    await test_db.close()

    uri1 = get_user_ws_endpoint(sender.id)
    uri2 = get_user_ws_endpoint(recipient.id)

    ws1 = await websockets.connect(uri1)
    ws2 = await websockets.connect(uri2)

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

        assert received_json['event'] == message['msg_type']
        data = received_json['data'] 
        assert data["sender_id"] == sender.id
        assert data["recipient_id"] == recipient.id
        assert data["fmt_msg_txt"] == message['fmt_msg_txt']
        # assert "unix_timestamp_ms" in received_json
    finally:
        await test_db.close()
        await ws1.close()
        await ws2.close()