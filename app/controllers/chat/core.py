import logging, json, time
from redis.asyncio import Redis
from datetime import datetime, timedelta, timezone
from redis.exceptions import RedisError, ConnectionError, TimeoutError

from . import (
    chat_dialogue_hset_key, 
    get_or_create_cached_chat,
)
from .schemas import ChatObjectSchema
from property_street_backend.config.settings import (
    DEBUG,
    CHAT_TTL,
    CHAT_LAZY_OFFLOAD_SCHEDULE,
)
from property_street_backend.log_config.logger_config import (
    log_message
)
from property_street_backend.app.controllers.ws_init import user_pend_pool_key
from property_street_backend.app.controllers.ws_init import get_client_channel_key
from property_street_backend.app.controllers.chat.utils.store import add_pending_msg_key_to_pool, chat_exception_handler
from property_street_backend.app.controllers.ws_init.ws_manager import ConnectionManager


websocket_logger = logging.getLogger("websocket")



async def update_cached_hset(
    chat_lazy_offload_schedule:int, 
    redis_client:Redis,
    cached_hset_key: str,
    chat_object: dict,
    ttl: int,
):
    lazy_timestamp = datetime.now(timezone.utc) + timedelta(seconds=chat_lazy_offload_schedule)
    await redis_client.hset(cached_hset_key, mapping={
        "chat_object": json.dumps(chat_object),
        "lazy_timestamp": lazy_timestamp
    })
    await redis_client.expire(cached_hset_key, ttl)


async def handle_chat(
    chat_obj: ChatObjectSchema,
    manager: ConnectionManager,
    chat_lazy_offload_schedule: int = CHAT_LAZY_OFFLOAD_SCHEDULE, 
    chat_ttl: int = CHAT_TTL,
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

    sender_ws = None

    cached_hset_key = chat_dialogue_hset_key(sender_id, recipient_id)
    
    if message_type=='incoming_message':
        try:
            # send the data to the recipient
            await manager.send_to_user(recipient_id, chat_obj)
            websocket_logger.info('**published to recipient\'s channel')
            
        except Exception as e:
            # when message fails to reach the recipient
            exc_msg = f"Failed to send message to user_{recipient_id}: {e}"
            await chat_exception_handler(
                chat_key_to_cache=cached_hset_key,
                redis_client=manager.redis,
                cache_for_user_id=recipient_id,
                exc_msg=exc_msg
            )
    elif message_type=='read_message':
        try:
            # update the data structure as message is sent/delivered
            # send the read notification to sender
            chat_obj['status'] = 'read'
            if sender_ws:
                await sender_ws.send_text(chat_obj)
            else: 
                raise ConnectionError
            if DEBUG:
                websocket_logger.info("Message read sent successfully to sender!")

            # get the cached chat if it exist else the empty object
            # update the status to sent
            # re-update the hset
            loaded_cached_chat = await get_or_create_cached_chat(recipient_id, sender_id, redis_client=redis_client) 
            unix_timestamp_ms = chat_obj['unix_timestamp_ms']
            loaded_cached_chat[str(unix_timestamp_ms)]['status'] = chat_obj
            lazy_timestamp = datetime.now(timezone.utc) + timedelta(seconds=chat_lazy_offload_schedule)
            await manager.redis.hset(cached_hset_key, mapping={
                "chat_object": json.dumps(loaded_cached_chat),
                "lazy_timestamp": lazy_timestamp
            })
            await manager.redis.expire(cached_hset_key, chat_ttl)
        except Exception as e:
            # when message fails to reach the sender
            await add_pending_msg_key_to_pool(
                chat_key=cached_hset_key,
                redis_client=manager.redis,
                user_id=sender_id,
            )
            
            if DEBUG:
                websocket_logger.error(f"Failed to notify sender of message read: {e}", exc_info=True)
            
            # log the message
            log_message(
                log_type = 'error',
                message = f"Failed to notify sender_{sender_id} of message read: {e}"
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
