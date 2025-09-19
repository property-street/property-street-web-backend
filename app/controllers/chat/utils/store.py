import json
from redis.asyncio import Redis
from datetime import datetime, timezone, timedelta

from .. import (
    get_or_create_cached_chat,
    chat_dialogue_hset_key,
)
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
from property_street_backend.app.controllers.ws_init import user_pend_pool_key, websocket_logger


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


async def add_pending_msg_lookup_token_to_user_pool(
    user_id: int,
    chat_key: str,
    timestamp: int,
    redis_client: Redis,
):
    """adds a given key 'chat_key:timestamp' to the messages field of 
    a user's pend-pool hset in the redis cache.

    Args:
        user_id (int): id of the user pend-pool to modify
        chat_key (str): key to be added to the messages field
        redis_client (Redis): redis session
        timestamp (int): unix timestamp of the message in milliseconds
    """
    pend_pool_key = user_pend_pool_key(user_id)
    messages = await redis_client.hget(pend_pool_key, 'messages')
    loaded_keys = json.loads(messages) if messages else []
    loaded_keys.append(f'{chat_key}:{timestamp}')
    key_set = set(loaded_keys) # removes duplicates
    await redis_client.hset(pend_pool_key, 'messages', json.dumps(list(key_set)))


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


def get_chat_ttl() -> int:
    """return in seconds the ttl of a dialouge chat hset 

    Returns:
        int: amount of seconds the hset should live
    """
    return TEST_CHAT_TTL if get_env() == 'test' else CHAT_TTL