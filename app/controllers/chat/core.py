import json, time
from redis.asyncio import Redis

from .schemas import ChatObjectSchema
from property_street_backend.config.settings import (
    DEBUG,
)
from property_street_backend.app.controllers.chat.utils.store import (
    chat_exception_handler,
)
from property_street_backend.app.controllers.ws_init import websocket_logger
from property_street_backend.app.controllers.ws_init.ws_manager import ConnectionManager
from property_street_backend.app.controllers.chat.utils.store import chat_exception_handler



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

    unix_timestamp_ms = chat_obj.get('unix_timestamp_ms',None)
    if not unix_timestamp_ms:
        unix_timestamp_ms = int(time.time() * 1000)
        chat_obj['unix_timestamp_ms'] = unix_timestamp_ms

    if message_type=='incoming_message':
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
    elif message_type=='read_message':
        try:
            # update the status to read
            # send the read notification to sender
            chat_obj['status'] = 'read'
            await manager.send_to_user(sender_id, chat_obj)
            if DEBUG:
                websocket_logger.info("**published to sender\'s channel!")
        except Exception as e:
            # when message fails to reach the sender
            exc_msg = f"Failed to notify sender of message read: {e}"
            await chat_exception_handler(
                redis_client = manager.redis,
                cache_for_user_id = sender_id,
                exc_msg = exc_msg,
                chat_obj = chat_obj
            )



async def cache_message(
    redis_client: Redis, 
    sender_id: int, 
    recipient_id: int, 
    message_obj: dict,
):
    key = f"msg_to_offload:{min(sender_id, recipient_id)}:{max(sender_id, recipient_id)}"
    timestamp = int(time.time())
    field = f"{sender_id}_{timestamp}"

    # add timestamp of the msg_obj
    message_obj['timestamp'] = timestamp
    
    # check if the field previously existed
    field_exists = await redis_client.hget(key, field)
    # Add or overwrite message to cache
    await redis_client.hset(key, field, json.dumps(message_obj))
    # if field is new, Append the key (timestamp) to a Redis list to maintain order
    if not field_exists:
        await redis_client.rpush(f"{key}:order", field)
    
    # get the ttl of the hset
    ttl = await redis_client.ttl(key)
    
    # If no TTL is set, initialize a TTL
    if ttl == -1:
        await redis_client.expire(key, 1800)  # 30 minutes
