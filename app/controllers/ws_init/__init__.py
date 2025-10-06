import time
import json
import logging
from typing import List
from redis.asyncio import Redis

agent_pend_pool_key = "pend_pool_agent_notification"
# score -> unix-timestamp in milliseconds

# active_authenticated_actors_set_key
aa_actors_set_key = "active_authenticated_actors"

agent_specific_channels = {
    'asset_request':'asset-request'
}
generic_channels = {
    'latest_assets': 'latest-assets',
    'roommates_finder': 'roommates-finder'
}

# channel categories or pong class
channel_categories = {
    'asset_request':'asset_request',
    'roommates_finder':'roommates_finder',
    'notification': 'notification'
}
pong_class = channel_categories
# references
notification_ref = {
    'roommates_finder': 'roommates_finder'
}

websocket_logger = logging.getLogger("websocket")

user_pend_pool_fields = {
    'notification': 'notifications'
}

def user_pend_pool_key(user_id:int,/)->str:
    """Accepts a user id and returns a proposed hset key 
    for holding data for a user on websocket failure.
        

    Args:
        user_id (int): id of a user

    Returns:
        str: a string used to query the redis cache for a specific user's data.
    """
    return f'pend_pool_{user_id}'

def get_client_channel_key(client_id):
    return f'channel_{client_id}'

def get_timestamp_milliseconds(timestamp:float)->float:
    return (timestamp if timestamp else time.time()) * 1000.0
    # int(datetime.now(timezone.utc).timestamp())


async def is_online(redis_client: Redis, user_id: int) -> bool:
    """Outputs if a user is online

    Args:
        redis_client (Redis): redis session.
        user_id (int): id of user checked on.

    Returns:
        bool: True if user is online else False.
    """
    return await redis_client.sismember(aa_actors_set_key, user_id)


async def add_pending_tokens_to_user_pool(
    user_id: int,
    tokens: str|int|List,
    pool_field: str,
    redis_client: Redis,
    *,
    replace: bool = False,
):
    websocket_logger.info(f"**Replace: {replace}")
    """adds a given token i.e'chat_key:timestamp' to the messages field of 
    a user's pend-pool hset in the redis cache.

    Args:
        user_id (int): id of the user pend-pool to modify
        token (str): token to be added to the `pool_key` field
        pool_field: pool field to modify
        redis_client (Redis): redis session
    """
    pend_pool_key = user_pend_pool_key(user_id)
    token_list = await redis_client.hget(pend_pool_key, pool_field)
    loaded_tokens:list = json.loads(token_list) if token_list else []
    token_is_list = isinstance(tokens,list)
    if replace:
        loaded_tokens = tokens if token_is_list else [tokens]
    else:
        loaded_tokens.extend(tokens) if token_is_list else loaded_tokens.append(tokens)
    token_set = set(loaded_tokens) # removes duplicates
    await redis_client.hset(pend_pool_key, pool_field, json.dumps(list(token_set)))