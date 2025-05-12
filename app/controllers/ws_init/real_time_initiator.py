import json
import logging
import asyncio
from fastapi import (
    WebSocket, 
    WebSocketDisconnect, 
    WebSocketException,
    status,
)
from typing import Dict
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession


from property_street_backend.config.settings import DEBUG
from property_street_backend.log_config.logger_config import (
    log_message
)
from property_street_backend.config.websocket_factory import (
    unauthenticated_ws,
    client_authenticated_ws,
)
from .utils import test_channel_handler
from .ws_manager import ConnectionManager
from .schemas import SocketInitializerKwargsSchema
from property_street_backend.app.controllers.chat.core import handle_chat
from property_street_backend.app.controllers.asset_request.utils import asset_request_channel_handler
from property_street_backend.app.database import get_db
from property_street_backend.app.controllers.notification.utils import dispatch_pending_notification
from property_street_backend.app.controllers.chat.dispatch_pending_chat import dispatch_pending_chat


websocket_logger = logging.getLogger("websocket")


async def websocket_initialiazer(
    websocket: WebSocket, 
    client_id: int,
    is_agent: True, 
    redis_client: Redis,
    db: AsyncSession,
    **kwargs: SocketInitializerKwargsSchema,
):
    """
    Websocket endpoint handler for real time functionality of the application

    Args:
        websocket (WebSocket): client's websocket
        client_id (int): client_id if authenticated
        redis_client (Redis): redis instance
        is_agent (bool): boolean to indicate if user's an agent if authenticated
        db (AsynSession): postgres instance
    
    Optional Keyword Args:
        last_n_timestamp (int): Timestamp of the last notification the client/client socket received 
    """

    pubsub = redis_client.pubsub()
    client_channel = f"channel_{client_id}"
    await pubsub.subscribe(client_channel)

    # handle pending transactions
    # asyncio.create_task(handle_pending_trx(
    #     user_id=client_id,
    #     redis_client=redis_client,
    #     ws=websocket,
    #     last_n_timestamp = kwargs.pop('last_timestamp',None),
    #     is_agent = is_agent,
    #     db = db
    # ))

    # Background listener for incoming messages to this user's channel
    async def listen_to_channel():
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode()
                try:
                    await websocket.send_text(data)
                except Exception as e:
                    websocket_logger.error(f"Failed to send message to client {client_id}: {e}")

    # Start listening
    asyncio.create_task(listen_to_channel())

    try:
        # Socket.send recipient that continuously waits for messages 
        # from the WebSocket client.
        # Handles incoming messages from the WebSocket client, 
        # publishes them to the Redis channel, 
        # and optionally sends an acknowledgment back to the client.
        while True: 
            # data received
            data = await websocket.receive_text() # keep alive

            # sends data to a channel according to the message structure
            await ws_reception_handler(
                data = data,
                redis_client = redis_client,
            )
            
            # redundant/ confirmation that the message has been received
            # await websocket.send_text(f"Message received: {data}") 
    
    except WebSocketDisconnect:
        await pubsub.unsubscribe(client_channel)
    except Exception as e:
        websocket_logger.error(f"Unexpected error on websocket for {client_id}: {e}")
        await pubsub.unsubscribe(client_channel)
        if DEBUG:
            websocket_logger.error(f"An error occured. reason:{e}", exc_info=True)

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
        parsed_data = json.loads(data)
    except json.JSONDecodeError:
        raise WebSocketException(code=status.WS_1003_UNSUPPORTED_DATA)

    if parsed_data.get("category") == "chat":
        await handle_chat(parsed_data, manager)


async def handle_pending_trx(
    redis_client: Redis,
    user_id: int,
    last_n_timestamp: int,
    is_agent: bool,
    websocket: WebSocket
):
    async for db in get_db():
        # dispatch pending notification
        await dispatch_pending_notification(
            last_timestamp=last_n_timestamp,
            redis_client = redis_client,
            db = db,
            is_agent = is_agent,
            ws = websocket,
            user_id = user_id
        )

        # dispatch pending chat
        await dispatch_pending_chat(
            redis_client = redis_client,
            user_id = user_id,
            db = db
        )