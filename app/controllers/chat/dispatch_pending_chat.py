import json
from typing import List
from fastapi import WebSocket
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import CachedMessageSchema
from .utils.offload_chat_data import offload_dialogue
from property_street_backend.app.initiator import logger
from property_street_backend.config.settings import DEBUG
from property_street_backend.app.controllers.ws_init import (
    user_pend_pool_key,
    channel_categories,
)
from property_street_backend.log_config.logger_config import (
    log_error,
    log_success,
)
from property_street_backend.app.controllers.ws_init import get_timestamp_milliseconds
from property_street_backend.app.controllers.chat.utils.store import (
    get_pending_messages,
    get_pending_message_tokens,
    get_chat_next_offload_schedule,
)

async def dispatch_pending_chat(
    *,
    redis_client: Redis,
    user_id: int,
    db: AsyncSession,
    websocket: WebSocket,
):
    """Retrieves all pending message token off a user's pend pool, 
    ping the message to the user, then offloads chat data to the database
    if the `lazy_timestamp` has been passed.

    Args:
        redis_client (Redis): redis instance
        user_id (int): id of the user
        db (AsyncSession): postgress session
        websocket (WebSocket): user websocket instance
    """
    if DEBUG:
        logger.info('*In dispatch_pending_chat function*')
    
    try:
        message_tokens: List[str] = await get_pending_message_tokens(user_id, redis_client)
        
        dialogue_keys = []
        msgs_to_dispatch = []
        for token in message_tokens: # token -> dialogue_key:timestamp
            dialogue_key, timestamp = (split_token:=token.split(':'))[0],split_token[1]
            dialogue_keys.append(dialogue_key)
            messages: dict[str, CachedMessageSchema] = await get_pending_messages(redis_client, dialogue_key)
            if messages and (chat_obj:= messages.get(timestamp)):
                msgs_to_dispatch.append(chat_obj)
        
        if msgs_to_dispatch:
            await websocket.send_json({
                'event': {
                    'class': channel_categories['chat'],
                    'type': 'pending_messages'
                },
                'data': msgs_to_dispatch 
            })

            # lazy offload
            unique_dialogue_keys = set(dialogue_keys)
            for key in unique_dialogue_keys:
                key: str # chat_(min_id)_(max_id)
                lazy_timestamp = await redis_client.hget(key, 'lazy_timestamp')
                if lazy_timestamp: 
                    # offload if the current timestamp is greater than the lazy timestamp
                    if get_timestamp_milliseconds() > float(lazy_timestamp): 
                        await offload_dialogue(
                            redis_client = redis_client,
                            db = db,
                            dialogue_key = key,
                        )
                else: 
                    lazy_timestamp_ms = get_chat_next_offload_schedule()
                    await redis_client.hset(key, 'lazy_timestamp', lazy_timestamp_ms)
            
            if unique_dialogue_keys and DEBUG:
                log_success(
                    'success',
                    f'{len(unique_dialogue_keys)} User:{user_id} pending threads successfully offloaded!'
                )
    except Exception as e:
        e_msg = f'Error offloading User:{user_id} pending chats! Reason: {e}'
        if DEBUG:
            logger.error(e_msg)
        log_error('error')
        raise e