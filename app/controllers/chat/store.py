import logging, json, time
from redis.asyncio import Redis
from datetime import datetime, timedelta, timezone
from redis.exceptions import RedisError, ConnectionError, TimeoutError

from . import chat_dialogue_zset_key
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
from property_street_backend.config.websocket_factory import get_client_socket_from_factory


websocket_logger = logging.getLogger("websocket")


async def get_or_create_cached_chat(recipient_id:int, sender_id:int, /, redis_client: Redis) -> dict:
    """Attempts to retrieve a chat object between two users if it exists, else
    returns and empty object

    Args:
        recipient_id (int): id of the chat recipient
        sender_id (int): id of the chat sender
        redis_client (Redis): redis session client

    Returns:
        dict: hash map of timestamp in milliseconds or an empty one
    """
    cached_hset_key = chat_dialogue_zset_key(sender_id, recipient_id)
    cached_chat = redis_client.hget(cached_hset_key, 'chat_object')
    return json.loads(cached_chat) if cached_chat else {}           


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
    data: ChatObjectSchema,
    redis_client: Redis,
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
    chat_obj = vars(data)
    message_type = chat_obj['msg_type']
    recipient_id = chat_obj['recipient_id']
    sender_id = chat_obj['sender_id']

    sender_ws = get_client_socket_from_factory(client_id=sender_id)
    recipient_ws = get_client_socket_from_factory(client_id=recipient_id)

    cached_hset_key = f'chat_{min(sender_id, recipient_id)}{max(sender_id, recipient_id)}'
    
    if message_type=='incoming_message':
        try:
            # send the data to the recipient
            # update the status of the message to delivered
            if recipient_ws:
                await recipient_ws.send_text(chat_obj)
            else:
                raise ConnectionError
            
            if DEBUG:
                websocket_logger.info(f"Message sent successfully to {recipient_id}!")
            
            # add a timestamp in milli_seconds
            # update the status to delivered
            # check that the hset exists
            # add the chat_obj under the timestamp
            unix_timestamp_ms = int(time.time() * 1000)
            chat_obj['unix_timestamp_ms'] = unix_timestamp_ms
            chat_obj['status'] = 'delivered'
            loaded_cached_chat = await get_or_create_cached_chat(recipient_id, sender_id, redis_client=redis_client)           
            loaded_cached_chat[unix_timestamp_ms] = chat_obj
            
            # update the lazy timestamp, ttl and chat_object of the hset
            lazy_timestamp = datetime.now(timezone.utc) + timedelta(seconds=chat_lazy_offload_schedule)
            await redis_client.hset(cached_hset_key, mapping={
                "chat_object": json.dumps(chat_obj),
                "lazy_timestamp": lazy_timestamp
            })
            
            try:          
                # update the sender's socket with the new chat-object
                if sender_ws:
                    await sender_ws.send_text(chat_obj)
                else:
                    raise ConnectionError
            except (ConnectionError, TimeoutError, RedisError) as e:
                await add_pending_msg_key_to_pool(
                    chat_key = cached_hset_key,
                    redis_client=redis_client,
                    user_id=sender_id,
                )
                # log the message
                log_message(
                    log_type = 'error',
                    message = f"Failed to send recipient-read to sender channel: {e}"
                )
        except (ConnectionError, TimeoutError, RedisError) as e:
            # when message fails to reach the recipient
            await add_pending_msg_key_to_pool(
                chat_key=cached_hset_key,
                redis_client=redis_client,
                user_id=recipient_id,
            )
            
            if DEBUG:
                websocket_logger.error(f"Failed to send message to user_{recipient_id}: {e}", exc_info=True)
            
            # log the message
            log_message(
                log_type = 'error',
                message = f"Failed to recipient-read to sender: {e}"
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
            await redis_client.hset(cached_hset_key, mapping={
                "chat_object": json.dumps(loaded_cached_chat),
                "lazy_timestamp": lazy_timestamp
            })
            await redis_client.expire(cached_hset_key, chat_ttl)
        except Exception as e:
            # when message fails to reach the sender
            await add_pending_msg_key_to_pool(
                chat_key=cached_hset_key,
                redis_client=redis_client,
                user_id=sender_id,
            )
            
            if DEBUG:
                websocket_logger.error(f"Failed to notify sender of message read: {e}", exc_info=True)
            
            # log the message
            log_message(
                log_type = 'error',
                message = f"Failed to notify sender_{sender_id} of message read: {e}"
            )


async def add_pending_msg_key_to_pool(
    user_id: int,
    chat_key: str,
    redis_client: Redis,
):
    """adds a given key 'chat_key' to the messages field of 
    a user's pend-pool zset in the redis cache.

    Args:
        user_id (int): id of the user pend-pool to modify
        chat_key (str): key to be added to the messages field
        redis_client (Redis): redis session
    """
    pend_pool_key = user_pend_pool_key(user_id)
    messages = await redis_client.hget(pend_pool_key, 'messages')
    loaded_keys = json.loads(messages) if messages else []
    loaded_keys.append(chat_key)
    await redis_client.hset(pend_pool_key, 'notification', json.dumps(loaded_keys))


#=== Still confused on the reasons for these functions ===#
async def clear_user_entry_off_pool(
    client_id: int,
    gen_pool: dict,
    redis_client: Redis
):
    try:
        # check if any transaction belongs to the user
        if gen_pool[str(client_id)]:
            # check for pending messages for the users
            if gen_pool[str(client_id)]['pending']['messages']:
                # delete the client's entry
                del gen_pool[str(client_id)]
                # update the redis set
                await redis_client.set(gen_pool_key,json.dumps(gen_pool))
    except Exception as e:
        if DEBUG:
            websocket_logger.error(f"Failed delete user message entry off pool: {e}", exc_info=True)
        
        # log the message
        log_message(
            log_type = 'error',
            message = f"Failed delete user message entry off pool: {e}"
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
