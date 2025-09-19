import json
from datetime import datetime, timezone
from fastapi import WebSocket
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from .utils.offload_chat_data import offload_dialogue
from property_street_backend.app.initiator import logger
from property_street_backend.config.settings import DEBUG
from property_street_backend.log_config.logger_config import log_message
from property_street_backend.app.controllers.ws_init import user_pend_pool_key
from property_street_backend.app.controllers.ws_init import get_timestamp_milliseconds
from property_street_backend.app.controllers.chat.utils.store import get_chat_next_offload_schedule

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
        pend_pool_key = user_pend_pool_key(user_id)
        message_tokens = await redis_client.hget(pend_pool_key, 'messages')
        
        dialogue_keys = []

        logger.info(f'**{message_tokens}')
        if message_tokens:
            msgs_to_dispatch = []
            token_list = json.loads(message_tokens)
            
            for token in token_list: # token -> dialogue_key:timestamp
                token: str
                split_token = token.split(':')
                dialogue_key = split_token[0]
                dialogue_keys.append(dialogue_key)
                lazy_timestamp = split_token[1]
                messages: dict[str, dict] = json.loads(await redis_client.hget(dialogue_key, 'messages'))
                if messages:
                    chat_obj = messages.get(lazy_timestamp)
                    if chat_obj:
                        msgs_to_dispatch.append(chat_obj)
            
            if msgs_to_dispatch:
                await websocket.send_json({
                    'event': {
                        'class': 'chat',
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
                    if get_timestamp_milliseconds() > int(lazy_timestamp): 
                        await offload_dialogue(
                            redis_client = redis_client,
                            db = db,
                            dialogue_key = key,
                        )
                else: 
                    lazy_timestamp_ms = get_chat_next_offload_schedule()
                    await redis_client.hset(key, 'lazy_timestamp', lazy_timestamp_ms)
            
            if dialogue_keys:
                log_message(
                    'success',
                    f'User:{user_id} pending chats successfully offloaded!'
                )
    except Exception as e:
        e_msg = f'Error offloading User:{user_id} pending chats! Reason: {e}'
        logger.error(e_msg)
        log_message('error',e_msg)
        raise e