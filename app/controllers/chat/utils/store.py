import json
from typing import List
from redis.asyncio import Redis
from datetime import datetime, timezone, timedelta


from ..schemas import CachedMessageSchema
from property_street_backend.config import get_env
from property_street_backend.config.settings import (
    DEBUG,
    CHAT_LAZY_OFFLOAD_SCHEDULE,
    TEST_CHAT_LAZY_OFFLOAD_SCHEDULE,
    CHAT_TTL,
    TEST_CHAT_TTL,
)
from property_street_backend.config.settings import DEBUG
from property_street_backend.log_config.logger_config import log_message
from property_street_backend.app.controllers.ws_init import (
    websocket_logger,
    user_pend_pool_key,
    user_pend_pool_fields,
    add_pending_tokens_to_user_pool,
)


def chat_dialogue_hset_key(sender_id:int, recipient_id:int, /)->str:
    """Accepts a sender and recipient id, and returns a hset key used to hold cached data for a dialogue chat.

    Args:
        sender_id (int): sender's user id
        recipient_id (int): recipient's user id

    Returns:
        str: hset key used to query redis cache.
    """
    return f'chat_{min(sender_id,recipient_id)}_{max(sender_id,recipient_id)}'


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
    cached_hset_key = chat_dialogue_hset_key(sender_id, recipient_id)
    cached_chat = await redis_client.hget(cached_hset_key, 'messages')
    return json.loads(cached_chat) if cached_chat else {}


async def cache_dialogue(
    chat_obj: dict,
    redis_client: Redis,
):
    # retrieve ids
    recipient_id = chat_obj['recipient_id']
    sender_id = chat_obj['sender_id']
    
    # get or create a cached hset for the dialogue
    # initialize an indicator to determine if it's new
    loaded_cached_chat = await get_or_create_cached_chat(recipient_id, sender_id, redis_client=redis_client) 
    loaded_cached_chat_is_new = loaded_cached_chat == {}
    
    # get or create the timestamp of the chat object
    # assign the chat_obj to the timestamp in the loaded_cached_chat
    server_timestamp_ms = chat_obj['server_timestamp_ms']
    loaded_cached_chat[str(server_timestamp_ms)] = chat_obj
    
    # get the chat dialogue key and make a mapping object for the hset
    cached_hset_key = chat_dialogue_hset_key(sender_id, recipient_id)
    await redis_client.hset(
        cached_hset_key, "messages", json.dumps(loaded_cached_chat)
    )

    # add a lazy timestamp to the hset_mapping if the loaded_chat is new
    if loaded_cached_chat_is_new:
        lazy_timestamp_unix_ms = get_chat_next_offload_schedule()
        await redis_client.hset(
            cached_hset_key, "lazy_timestamp", lazy_timestamp_unix_ms
        )
    
    # cache the data and set an expiry
    # await redis_client.expire(cached_hset_key, get_chat_ttl())


async def get_pending_message_tokens(client_id: int, redis_client: Redis) -> List:
    pool_key = user_pend_pool_key(client_id)
    data = await redis_client.hget(pool_key, user_pend_pool_fields['message'])
    return (json.loads(data) if data else [])


async def add_pending_msg_lookup_token_to_user_pool(
    user_id: int,
    chat_key: str,
    timestamp_ms: int,
    redis_client: Redis,
    **kwargs,
):
    """adds a given key 'chat_key:timestamp' to the messages field of 
    a user's pend-pool hset in the redis cache.

    Args:
        user_id (int): id of the user pend-pool to modify
        chat_key (str): key to be added to the messages field
        redis_client (Redis): redis session
        timestamp (int): unix timestamp of the message in milliseconds
    """
    token = f'{chat_key}:{timestamp_ms}'
    await add_pending_tokens_to_user_pool(
        user_id=user_id, 
        tokens=token, 
        pool_field=user_pend_pool_fields['message'], 
        redis_client=redis_client,
        **kwargs
    )


async def add_multi_pending_msg_tokens_to_user_pool(
    chat_tokens: str|List[str],
    redis_client: Redis,
    client_id: int,
    **kwargs
):
    """Caches Notifiation model ids to redis

    Args:
        chat_tokens (str | List[str]): string or list of string of the format '{dialogue_key}_{timestamp_ms}'
        redis_client (Redis): redis instance
        client_id (int): user_id for identifying pool
        kwargs: 
            replace: bool = False: Determines if the pool should be replaced by the current input
    """
    await add_pending_tokens_to_user_pool(
        user_id=client_id, 
        tokens=chat_tokens, 
        pool_field=user_pend_pool_fields['message'], 
        redis_client=redis_client,
        **kwargs
    )


async def chat_exception_handler(
    redis_client: Redis,
    cache_for_user_id: int,
    exc_msg: str,
    chat_obj: dict
):
    """Persist the message on the cache, add a token to the user's pend pool
    to enable selective retrieval on intended recipient's reconnection, and 
    logs the exception to the custom logger file.

    Args:
        redis_client (Redis): redis instance
        cache_for_user_id (int): receiver id before failure
        exc_msg (str): description of error
        chat_obj (dict): message dictionary
    """
    if DEBUG:
        websocket_logger.error(exc_msg, exc_info=True)

    recipient_id = chat_obj['recipient_id']
    sender_id = chat_obj['sender_id']
    server_timestamp_ms = chat_obj['server_timestamp_ms']
    cache_hset_key = chat_dialogue_hset_key(sender_id, recipient_id)
    
    # cache the message
    await cache_dialogue(chat_obj, redis_client)
    
    # add the message lookup token to the user pend pool
    await add_pending_msg_lookup_token_to_user_pool(
        cache_for_user_id, 
        cache_hset_key, 
        server_timestamp_ms, 
        redis_client
    )

    # log the message
    log_message(
        log_type = 'error',
        message = exc_msg
    )


def get_chat_next_offload_schedule() -> int:
    """adds the current datetime to a given duration (in seconds) of chat longetivity before offload
    to the database using a lazy mechanism. 

    Returns:
        int: unix timestamp of the next lazy offload timestamp
    """
    chat_lazy_offload_schedule: int = TEST_CHAT_LAZY_OFFLOAD_SCHEDULE if get_env() == 'test' else CHAT_LAZY_OFFLOAD_SCHEDULE 
    lazy_timestamp = datetime.now(timezone.utc) + timedelta(seconds=chat_lazy_offload_schedule)
    return int(lazy_timestamp.timestamp())


async def get_pending_messages(redis_client: Redis, dialogue_key: str)->dict[str, CachedMessageSchema]:
    messages = await redis_client.hget(dialogue_key, 'messages')
    return  json.loads(messages) if messages else {}


def get_chat_ttl() -> int:
    """return in seconds the ttl of a dialouge chat hset 

    Returns:
        int: amount of seconds the hset should live
    """
    return TEST_CHAT_TTL if get_env() == 'test' else CHAT_TTL