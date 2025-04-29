import json
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.config.settings import (
    CHAT_LAZY_OFFLOAD_SCHEDULE,
    TEST_CHAT_LAZY_OFFLOAD_SCHEDULE
)
from .utils.offload_chat_data import offload_chat_data
from property_street_backend.config.context_sessions import get_env
from property_street_backend.log_config.logger_config import log_message
from property_street_backend.app.controllers.ws_init import user_pend_pool_key


async def dispatch_pending_chat(
    *,
    redis_client: Redis,
    user_id: int,
    db: AsyncSession,
):
    try:
        pend_pool_key = user_pend_pool_key(user_id)
        messages = await redis_client.hget(pend_pool_key, 'messages')
        
        if messages:
            msg_key_list = json.loads(messages)
            for key in msg_key_list:
                split_key = key.split('_')
                min_id = split_key[1]
                max_id = split_key[2]
                env = get_env()
                chat_lazy_offload_schedule = TEST_CHAT_LAZY_OFFLOAD_SCHEDULE if env == 'test' else CHAT_LAZY_OFFLOAD_SCHEDULE
                await offload_chat_data(
                    redis_client=redis_client,
                    db=db,
                    min_id=min_id,
                    max_id=max_id,
                    chat_lazy_offload_schedule = chat_lazy_offload_schedule
                )
        log_message(
            'success',
            f'User:{user_id} pending chats successfully offloaded!'
        )
    except Exception as e:
        log_message(
            'error',
            f'Error offloading User:{user_id} pending chats! Reason: {e}'
        )