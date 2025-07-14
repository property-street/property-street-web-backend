from fastapi import WebSocket
from redis.asyncio import Redis
from typing import Callable, Awaitable
from redis.exceptions import ConnectionError

from property_street_backend.config.settings import DEBUG
from property_street_backend.app.controllers.ws_init import (
    websocket_logger,
)
from . import chat_dialogue_hset_key
from property_street_backend.app.controllers.chat.utils.store import (
    cache_dialogue,
    chat_exception_handler,
)


async def pubsub_chat_handler(websocket: WebSocket, chat_obj: dict, redis_client: Redis, send_to_user: Callable[[int, dict], Awaitable[None]]):
    if DEBUG:
        websocket_logger.info('**pubsub_chat_handler invoked')

    # deserialize the message 
    recipient_id = chat_obj['recipient_id']
    sender_id = chat_obj['sender_id']
    message_type = chat_obj['msg_type']
    
    # cached_hset_key of the dialogue
    dialogue_hset_key = chat_dialogue_hset_key(sender_id, recipient_id)

    # change the status of the chat object to sent, and add a timestamp
    if chat_obj['status'] == 'unsent':
        chat_obj['status'] = 'sent'

    # get new chat status
    chat_status = chat_obj['status']

    # send the message
    try:
        if websocket:
            await websocket.send_json({
                'event': {
                    'type': message_type,
                    'class': 'chat'
                },
                'data': chat_obj
            })
            if DEBUG:
                websocket_logger.info(f"Message sent successfully to receiver!")
        else: 
            if DEBUG:
                websocket_logger.info(f"Instance's socket disconnected at the moment!")
            raise ConnectionError
    except Exception as e:
        if chat_status == 'sent':
            # when message fails to reach the recipient
            exc_msg = f"Failed to send message to user_{recipient_id}: {e}"
            cache_for_user_id = recipient_id,
        elif chat_status == 'delivered':
            exc_msg = f"delivered receipt fails to hit sender's socket. Reason: {e}!"
            cache_for_user_id = sender_id,
        elif chat_status == 'read':
            exc_msg = f"read receipt fails to hit sender's socket. Reason: {e}!"
            cache_for_user_id = sender_id,
        # call the exception handler
        await chat_exception_handler(
            redis_client = redis_client,
            cache_for_user_id = cache_for_user_id,
            exc_msg = exc_msg,
            chat_obj = chat_obj
        )
        raise e # This is raised so the remaining function body is not executed

    if chat_status == 'sent': # means an incoming-message was just sent to the recipient
        chat_obj['status'] = 'delivered'
        chat_obj['msg_type'] = 'delivered_message'

        # publish the new chat status to the sender's channel
        try:
            await send_to_user(sender_id, chat_obj)
            if DEBUG:
                websocket_logger.info('**published to sender\'s channel')

        except Exception as e:
            # when the receipt fails to reach the sender's channel
            exc_msg = f"Receipt failed to hit sender's channel. Reason: {e}!"
            await chat_exception_handler(
                cache_hset_key = dialogue_hset_key,
                redis_client = redis_client,
                cache_for_user_id = sender_id,
                exc_msg = exc_msg
            )

    # cache the dialogue
    await cache_dialogue( chat_obj, redis_client )