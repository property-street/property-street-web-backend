from fastapi import WebSocket
from redis.asyncio import Redis
from typing import Callable, Awaitable
from redis.exceptions import ConnectionError

from .enums import MessageTypes, MessageStatus
from property_street_backend.config.settings import DEBUG
from property_street_backend.app.controllers.ws_init import (
    websocket_logger,
)
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
    
    # change the status of the chat object to sent, and add a timestamp
    if message_type == MessageTypes.outbound_message.value:
        chat_obj['msg_type'] = MessageTypes.inbound_message.value
        chat_obj['status'] = MessageStatus.sent.value
    elif message_type == MessageTypes.delivered_message.value:
        chat_obj['status'] = MessageStatus.delivered.value
    elif message_type == MessageTypes.read_message.value:
        chat_obj['msg_type'] = MessageTypes.completed.value

    # get updated message_type and status
    message_type = chat_obj['msg_type']
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
        if chat_status == MessageStatus.sent.value:
            # Message fails to reach the recipient
            exc_msg = f"Failed to send message to user_{recipient_id}: {e}"
            cache_for_user_id = recipient_id,
        elif chat_status == MessageStatus.delivered.value:
            exc_msg = f"delivered receipt fails to hit sender's socket. Reason: {e}!"
            cache_for_user_id = sender_id,
        elif chat_status == MessageStatus.read.value:
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

    # cache the dialogue
    await cache_dialogue( chat_obj, redis_client )