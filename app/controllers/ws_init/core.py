import json
import logging
from fastapi import (
    WebSocketException,
    status,
)
from redis.asyncio import Redis

from .ws_manager import ConnectionManager
from property_street_backend.app.controllers.chat.core import handle_chat


websocket_logger = logging.getLogger("websocket")


async def ws_reception_handler(
    data: str,
    manager: ConnectionManager,
):
    """Called when a message is sent from a socket client

    Args:
        data (str): serialized object holding the message
        manager (ConnectionManager): class object managing socket connection 
    """
    try:
        parsed_data: dict = json.loads(data)
    except json.JSONDecodeError:
        raise WebSocketException(code=status.WS_1003_UNSUPPORTED_DATA)

    if parsed_data.get("category") == "chat":
        await handle_chat(parsed_data, manager)


async def delete_pend_pool_when_empty(
    redis_client: Redis,
    pend_pool_key: str
):
    if await redis_client.exists(pend_pool_key):
        messages = await redis_client.hget(pend_pool_key, 'messages')
        notifications = await redis_client.hget(pend_pool_key, 'notifications')
        if not messages and not notifications:    
            await redis_client.delete(pend_pool_key)
