import json
from datetime import datetime, timezone
from fastapi import WebSocket
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from .utils.offload_chat_data import offload_chat_data
from property_street_backend.log_config.logger_config import log_message
from property_street_backend.app.controllers.ws_init import user_pend_pool_key


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
    try:
        pend_pool_key = user_pend_pool_key(user_id)
        messages = await redis_client.hget(pend_pool_key, 'messages')
        
        dialogue_keys = []
        if messages:
            msg_to_dispatch = []
            token_list = json.loads(messages)
            for token in token_list: # token -> dialogue_key:timestamp
                token: str
                splitted_token = token.split(':')
                dialogue_key = splitted_token[0]
                dialogue_keys.append(dialogue_key)
                timestamp = splitted_token[1]
                loaded_serialized_chat:dict = json.loads(await redis_client.hget(dialogue_key, 'chat_object'))
                if loaded_serialized_chat:
                    chat_obj = loaded_serialized_chat.get(str(timestamp))
                    if chat_obj:
                        msg_to_dispatch.append(chat_obj)
            if msg_to_dispatch:
                websocket.send_json({
                    'event': {
                        'class': 'chat',
                        'type': 'pending messages'
                    },
                    'data': msg_to_dispatch 
                })


            # lazy offload
            for key in dialogue_keys:
                key: str # chat_(min_id)_(max_id)
                timestamp = await redis_client.hget(key, 'lazy_timestamp')
                if timestamp: 
                    if int(timestamp) > int(datetime.now(timezone.utc).timestamp()):
                        continue # means lazy offload is still in the future
                split_key = key.split('_')
                min_id = split_key[1]
                max_id = split_key[2]
                await offload_chat_data(
                    redis_client = redis_client,
                    db = db,
                    min_id = min_id,
                    max_id = max_id,
                )
            
            if dialogue_keys:
                log_message(
                    'success',
                    f'User:{user_id} pending chats successfully offloaded!'
                )
    except Exception as e:
        log_message(
            'error',
            f'Error offloading User:{user_id} pending chats! Reason: {e}'
        )