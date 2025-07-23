import json
import pytest
import asyncio
import websockets
from sqlalchemy import select
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from ...utils import get_user_ws_endpoint
from .. import message as message_template
from property_street_backend.app.models import Message
from property_street_backend.app.controllers.chat import chat_dialogue_hset_key
from property_street_backend.tests.auth.test_user_creation import create_test_user
from property_street_backend.app.schemas.auth_schemas import UserRegistrationSchema
from property_street_backend.app.controllers.auth.services import fetch_access_token
from property_street_backend.config.postgres_connection_manager import get_postgres_instance
from property_street_backend.app.controllers.ws_init import user_pend_pool_key, get_timestamp_milliseconds


@pytest.mark.asyncio
async def test_offload_dialogue( app_subprocess, sessions_fixture ):
    test_db = None
    redis_client = None
    recipient_ws = None

    try:
        async for fixture_obj in sessions_fixture:
            test_db: AsyncSession = fixture_obj['db']
            redis_client: Redis = fixture_obj['redis_client']
            break

        sender = await create_test_user(test_db)
        recipient = await create_test_user(test_db, UserRegistrationSchema(
            username='recipient',
            email='recipient@example.com',
            password='strongpassword',
            first_name = 'recipient'
        ))
        recipient_id = recipient.id
        sender_id = sender.id

        server_timestamp_ms = get_timestamp_milliseconds()
        # fabricate a message map
        messages = {(ts := i + server_timestamp_ms):{
            **message_template,
            "sender_id": sender_id,
            "recipient_id": recipient_id,
            "server_timestamp_ms": ts,
        } for i in range(3)}
        timestamps = [int(key) for key in messages.keys()]

        dialogue_hset_key = chat_dialogue_hset_key(sender_id, recipient_id)
        # dump the message into the dialogue cache
        await redis_client.hset(dialogue_hset_key, "messages", json.dumps(messages))
        await redis_client.hset(dialogue_hset_key, "lazy_timestamp", server_timestamp_ms)
        # formulate tokens for the message and cache them in the user's pendpool
        pend_pool_message_tokens = [
            f'{dialogue_hset_key}:{timestamp}'
            for timestamp in timestamps
        ]
        pend_pool_key = user_pend_pool_key(recipient_id)
        await redis_client.hset(pend_pool_key, "messages", json.dumps(pend_pool_message_tokens))
            
        # get authorization tokens and connect
        recipient_token = fetch_access_token(recipient)['access_token']
        recipient_ws = await websockets.connect( 
            get_user_ws_endpoint( recipient_token )
        )


        received_data = await asyncio.wait_for(recipient_ws.recv(), timeout = 60)
        loaded_received_data: dict = json.loads(received_data)
        event = loaded_received_data['event']
        assert event['type'] == 'pending_messages'
        chat_obj = loaded_received_data.get('data')
        assert isinstance(chat_obj,list) and (len(chat_obj) == len(timestamps))

        # sleep a lil
        await asyncio.sleep(5)
 
        await test_db.refresh(sender)
        await test_db.refresh(recipient)
        stmt = (
            select(Message)
            .where(Message.server_timestamp_ms.in_(timestamps))
            .order_by(Message.server_timestamp_ms.asc())
        )
        result = await test_db.execute(stmt)
        messages = result.scalars().all()
        assert len(messages) == len(timestamps)
 
        assert not await redis_client.exists(dialogue_hset_key)
    finally:
        if recipient_ws:
            await recipient_ws.close()
        if test_db:
            await test_db.close()
        if redis_client:
            await redis_client.aclose()