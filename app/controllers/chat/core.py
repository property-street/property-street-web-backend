import json, time
from redis.asyncio import Redis

from .enums import MessageTypes
from .schemas import ChatObjectSchema
from property_street_backend.config.settings import (
    DEBUG,
)
from property_street_backend.app.controllers.chat.utils.store import (
    cache_dialogue,
    chat_exception_handler,
)
from property_street_backend.app.controllers.ws_init import websocket_logger
from property_street_backend.app.controllers.ws_init.ws_manager import ConnectionManager
from property_street_backend.app.controllers.ws_init import get_timestamp_milliseconds



async def handle_chat(
    chat_obj: ChatObjectSchema,
    manager: ConnectionManager,
):
    """Called when a chat object is sent to the server socket.

    Args:
        data (ChatObjectSchema): contains the chat metadata; like the sender_id, recipient_id, message, etc.
        redis_client (Redis): used to handle caching of the chat data.
        chat_ttl (int): limited time in seconds a cached obj has to persist on redis.
        chat_lazy_offload_schedule (int): a marker which tells if a cached chat is due for a migration to the database.
    """
    message_type = chat_obj['msg_type']
    recipient_id = chat_obj['recipient_id']
    sender_id = chat_obj['sender_id']

    server_timestamp_ms = chat_obj.get('server_timestamp_ms')
    if not server_timestamp_ms:
        server_timestamp_ms = get_timestamp_milliseconds()
        chat_obj['server_timestamp_ms'] = server_timestamp_ms


    if message_type == MessageTypes.outbound_message.value:
        try:
            # send the data to the recipient
            await manager.send_to_user(recipient_id, chat_obj)
            if DEBUG:
                websocket_logger.info('**published to recipient\'s channel')
            
        except Exception as e:
            # when message fails to reach the recipient
            exc_msg = f"Failed to send message to user_{recipient_id}: {e}"
            await chat_exception_handler(
                redis_client = manager.redis,
                cache_for_user_id = recipient_id,
                exc_msg = exc_msg,
                chat_obj = chat_obj
            )
    elif (message_type==MessageTypes.delivered_message.value) or (message_type == MessageTypes.read_message.value):
        try:
            # send the data to the sender
            await manager.send_to_user(sender_id, chat_obj)
            if DEBUG:
                websocket_logger.info('**published to sender\'s channel')
            
        except Exception as e:
            # when message fails to reach the sender
            exc_msg = f"Failed to send message to user_{recipient_id}: {e}"
            await chat_exception_handler(
                redis_client = manager.redis,
                cache_for_user_id = recipient_id,
                exc_msg = exc_msg,
                chat_obj = chat_obj
            )