import json
import time
from fastapi import WebSocket
from redis.asyncio import Redis
from typing import Callable, Awaitable
from redis.exceptions import ConnectionError
from datetime import datetime, timedelta, timezone

from property_street_backend.config.settings import (
    DEBUG,
    CHAT_TTL,
    CHAT_LAZY_OFFLOAD_SCHEDULE,
    TEST_CHAT_LAZY_OFFLOAD_SCHEDULE,
)
from property_street_backend.app.controllers.ws_init import (
    websocket_logger,
)
from . import chat_dialogue_hset_key
from property_street_backend.config.context_sessions import get_env
from property_street_backend.log_config.logger_config import log_message
from property_street_backend.app.controllers.chat import get_or_create_cached_chat
from property_street_backend.app.controllers.chat.utils.store import chat_exception_handler


async def pubsub_chat_handler(websocket: WebSocket, chat_obj: dict, redis_client: Redis, send_to_user: Callable[[int, dict], Awaitable[None]]):
    if DEBUG:
        websocket_logger.info('**pubsub_chat_handler invoked')

    # deserialize the message 
    recipient_id = chat_obj['recipient_id']
    sender_id = chat_obj['sender_id']
    message_type = chat_obj['msg_type']
    
    # chat lazy offload schedule, cached_hset_key of the dialogue, and redis_client retrieved
    chat_lazy_offload_schedule: int = TEST_CHAT_LAZY_OFFLOAD_SCHEDULE if get_env() == 'test' else CHAT_LAZY_OFFLOAD_SCHEDULE 
    dialogue_hset_key = chat_dialogue_hset_key(sender_id, recipient_id)

    # change the status of the chat object to sent, and add a timestamp
    if chat_obj['status'] == 'unsent':
        chat_obj['status'] = 'sent'
        unix_timestamp_ms = int(time.time() * 1000)
        chat_obj['unix_timestamp_ms'] = unix_timestamp_ms

    # send the message
    try:
        if websocket:
            await websocket.send_json({
                'event': message_type,
                'data': chat_obj
            })
        else: 
            if DEBUG:
                websocket_logger.info(f"Instance's socket disconnected at the moment!")
            raise ConnectionError
    except Exception as e:
        if chat_status == 'sent':
            # when message fails to reach the recipient
            exc_msg = f"Failed to send message to user_{recipient_id}: {e}"
            await chat_exception_handler(
                chat_key_to_cache=dialogue_hset_key,
                redis_client=redis_client,
                cache_for_user_id=recipient_id,
                exc_msg=exc_msg
            )
        elif chat_status == 'delivered':
            exc_msg = f"Receipt failed to hit sender's socket. Reason: {e}!"
            await chat_exception_handler(
                chat_key_to_cache = dialogue_hset_key,
                redis_client = redis_client,
                cache_for_user_id = sender_id,
                exc_msg = exc_msg
            )

    chat_status = chat_obj['status']   
    if chat_status == 'sent': # means an incoming-message was just sent to the recipient
        if DEBUG:
            websocket_logger.info(f"Message sent successfully to {recipient_id}!")

        chat_obj['status'] = 'delivered'
        chat_obj['msg_type'] = 'delivered_message'
        loaded_cached_chat = await get_or_create_cached_chat(recipient_id, sender_id, redis_client=redis_client)           
        loaded_cached_chat[unix_timestamp_ms] = chat_obj
        
        # update the lazy timestamp, ttl and chat_object of the hset
        lazy_timestamp = datetime.now(timezone.utc) + timedelta(seconds=chat_lazy_offload_schedule)
        lazy_timestamp_unix_ms = int(lazy_timestamp.timestamp() * 1000)
        await redis_client.hset(dialogue_hset_key, mapping={
            "chat_object": json.dumps(loaded_cached_chat),
            "lazy_timestamp": lazy_timestamp_unix_ms
        })

        # publish the new chat status to the sender's channel
        try:
            await send_to_user(sender_id, chat_obj)
        except Exception as e:
            # when the receipt fails to reach the sender's channel
            exc_msg = f"Receipt failed to hit sender's channel. Reason: {e}!"
            await chat_exception_handler(
                chat_key_to_cache = dialogue_hset_key,
                redis_client = redis_client,
                cache_for_user_id = sender_id,
                exc_msg = exc_msg
            )
    elif chat_status == 'delivered': # means a receipt was just sent to the sender; do nothing
        pass
