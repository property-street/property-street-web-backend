import json
from redis.asyncio import Redis

from property_street_backend.config.settings import DEBUG
from property_street_backend.log_config.logger_config import log_message
from property_street_backend.app.controllers.ws_init import user_pend_pool_key, websocket_logger


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


async def chat_exception_handler(
    chat_key_to_cache: str,
    redis_client: Redis,
    cache_for_user_id: int,
    exc_msg: str
):
    if DEBUG:
        websocket_logger.error(exc_msg, exc_info=True)
    
    # log the message
    await add_pending_msg_key_to_pool(
        chat_key=chat_key_to_cache,
        redis_client=redis_client,
        user_id=cache_for_user_id,
    )

    # log the message
    log_message(
        log_type = 'error',
        message = exc_msg
    )