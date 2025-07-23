import json
import pytest
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from .. import message as message_template
from property_street_backend.app.controllers.ws_init import user_pend_pool_key, get_timestamp_milliseconds
from property_street_backend.app.controllers.chat import chat_dialogue_hset_key
from property_street_backend.tests.auth.test_user_creation import create_test_user
from property_street_backend.app.controllers.chat import get_or_create_cached_chat
from property_street_backend.app.controllers.chat.utils.store import chat_exception_handler


@pytest.mark.asyncio
async def test_dispatch_pending_messages_manual( sessions_fixture ):
    test_db = None

    try:
        async for fixture_obj in sessions_fixture:
            test_db: AsyncSession = fixture_obj['db']
            redis_client: Redis = fixture_obj['redis_client']
            break

        user = await create_test_user(test_db)
        # user_token = fetch_access_token(user)['access_token']
        user_id = user.id

        sender_id = 5
        recipient_id = user_id
        server_timestamp_ms = get_timestamp_milliseconds()
        message = {
            **message_template,
            "sender_id": sender_id,
            "recipient_id": recipient_id,
            "server_timestamp_ms": server_timestamp_ms
        }
        await chat_exception_handler(
            redis_client,
            user_id,
            exc_msg = f"Failed to send message to user_{user_id}",
            chat_obj = message
        )

        dialogue_hset_key = chat_dialogue_hset_key(sender_id, recipient_id)

        # assert that the chat_exception_handler stored the chat in the hset
        cached_thread = await get_or_create_cached_chat(recipient_id, sender_id, redis_client)
        cached_message = list(cached_thread.values())[0]
        # and the server_timestamp_ms field is present in the modified message object
        assert "server_timestamp_ms" in cached_message


        # assert that chat token was added to the user's pend pool
        pend_pool_key = user_pend_pool_key(user_id)
        token_list: list[str] = json.loads(await redis_client.hget(pend_pool_key, 'messages'))
        split_token = token_list[0].split(':')
        assert split_token[0] == dialogue_hset_key
        assert split_token[1] == str(server_timestamp_ms)
    finally:
        await test_db.close()