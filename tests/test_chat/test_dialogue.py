import json
import pytest
import asyncio
import websockets
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from ..utils import get_user_ws_endpoint
from . import message as message_template
from property_street_backend.app.initiator import get_redis
from property_street_backend.tests.auth import create_test_user
from property_street_backend.app.controllers.chat.schemas import CachedMessageSchema as MessageSchema
from property_street_backend.app.controllers.auth.services import fetch_access_token
from property_street_backend.app.schemas.auth_schemas import UserRegistrationSchema
from property_street_backend.app.controllers.chat.enums import MessageTypes, MessageStatus
from property_street_backend.app.controllers.chat import chat_dialogue_hset_key, get_or_create_cached_chat


@pytest.mark.asyncio
async def test_dialogue( app_subprocess, client__fixture ):
    test_db: AsyncSession = client__fixture['db']
    redis_client: Redis = client__fixture['redis_client']

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
        message = MessageSchema.model_validate({
            "sender_id": sender_id,
            "recipient_id": recipient_id,
            **message_template,
        }).model_dump()

        await sender_ws.send(json.dumps(message))

        server_timestamp_ms: int = None

        chat_obj = None
        async def recipient_receipt_check():
            nonlocal chat_obj
            nonlocal server_timestamp_ms
            received_data = await recipient_ws.recv()
            loaded_received_data: dict = json.loads(received_data)
            inbound_value = MessageTypes.inbound_message.value
            sent_value =MessageStatus.sent.value

            event = loaded_received_data.get('event') 
            assert event['type'] == inbound_value
            assert event['class'] == 'chat'

            chat_obj = loaded_received_data.get('data')
            assert chat_obj['status'] == sent_value
            assert chat_obj['msg_type'] == inbound_value
            assert "server_timestamp_ms" in chat_obj
            server_timestamp_ms = chat_obj['server_timestamp_ms']

            # check that the dialogue exist in the cache
            async for redis_client in get_redis():
                assert await redis_client.exists(dialogue_hset_key)
                assert server_timestamp_ms
                dialogue_hset_lazy_timestamp = int(await redis_client.hget(dialogue_hset_key,'lazy_timestamp'))
                assert dialogue_hset_lazy_timestamp > 0
                dialogue_hset_messages:dict = await get_or_create_cached_chat(recipient_id, sender_id, redis_client)
                current_chat_obj = dialogue_hset_messages.get(str(server_timestamp_ms))
                assert current_chat_obj['status'] == sent_value
                assert current_chat_obj['msg_type'] == inbound_value
                break

        async def receipt_check_group():
            async with asyncio.TaskGroup() as tg:
                tg.create_task(recipient_receipt_check())
                # tg.create_task(sender_receipt_check())
        
        await asyncio.wait_for(receipt_check_group(), timeout = 60)



        #--* modify the chat object and notify the sender *--#
        delivered_value = MessageTypes.delivered_message.value
        status_delivered_value = MessageStatus.delivered.value
        # receive the message on the sender's socket to verify the status
        # make assertions on the chat hset to verify sync of change
        chat_obj['msg_type'] = delivered_value
        await recipient_ws.send(json.dumps(chat_obj))
        
        recv_data:dict = json.loads(await asyncio.wait_for(sender_ws.recv(), timeout = 60))
        event = recv_data['event'] 
        assert event['type'] == delivered_value
        mod_chat_obj = recv_data.get('data')
        assert mod_chat_obj['msg_type'] == delivered_value
        assert mod_chat_obj['status'] == status_delivered_value

        # sleep a lil
        await asyncio.sleep(5)

        async for redis_client in get_redis():
            dialogue_hset_messages:dict = await get_or_create_cached_chat(recipient_id, sender_id, redis_client)
            current_chat_obj = dialogue_hset_messages.get(str(server_timestamp_ms))
            assert current_chat_obj['status'] == status_delivered_value
            assert current_chat_obj['msg_type'] == delivered_value
            break



        #--* modify the chat object to read *--#
        read_value = MessageTypes.read_message.value
        completed_value = MessageTypes.completed.value
        read_status_value = MessageStatus.read.value
        # receive the message on the sender's socket to verify the status
        # make assertions on the chat hset to verify sync of change
        chat_obj['msg_type'] = read_value
        chat_obj['status'] = read_status_value
        await recipient_ws.send(json.dumps(chat_obj))
        
        recv_data:dict = json.loads(await asyncio.wait_for(sender_ws.recv(), timeout = 60))
        event = recv_data['event'] 
        assert event['type'] == completed_value
        mod_chat_obj = recv_data.get('data')
        assert mod_chat_obj['msg_type'] == completed_value
        assert mod_chat_obj['status'] == read_status_value

        # sleep a lil
        await asyncio.sleep(5)

        async for redis_client in get_redis():
            dialogue_hset_messages:dict = await get_or_create_cached_chat(recipient_id, sender_id, redis_client)
            current_chat_obj = dialogue_hset_messages.get(str(server_timestamp_ms))
            assert current_chat_obj['status'] == read_status_value
            assert current_chat_obj['msg_type'] == completed_value
            break


    finally:
        if sender_ws:
            await sender_ws.close()
        if recipient_ws:
            await recipient_ws.close()