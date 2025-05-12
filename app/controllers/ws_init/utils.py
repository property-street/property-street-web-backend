from redis.asyncio import Redis


from property_street_backend.log_config.logger_config import log_message
from property_street_backend.config.websocket_factory import get_instance_ws
from property_street_backend.app.controllers.ws_init import (
    websocket_logger,
    get_client_channel_key,
)
from property_street_backend.config import get_env
from property_street_backend.app.controllers.chat import get_or_create_cached_chat
from property_street_backend.app.controllers.chat.utils.store import chat_exception_handler
from property_street_backend.config.context_sessions import get_redis_based_on_context


async def delete_pend_pool_when_empty(
    redis_client: Redis,
    pend_pool_key: str
):
    if await redis_client.exists(pend_pool_key):
        messages = await redis_client.hget(pend_pool_key, 'messages')
        notifications = await redis_client.hget(pend_pool_key, 'notifications')
        if not messages and not notifications:    
            await redis_client.delete(pend_pool_key)


async def test_channel_handler(message):
    websocket_logger.info(f'Channel handler executed with message {message}')