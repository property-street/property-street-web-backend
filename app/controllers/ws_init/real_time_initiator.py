import json
import logging
import asyncio
from fastapi import (
    WebSocket, 
    WebSocketDisconnect, 
)
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession


from property_street_backend.config.settings import DEBUG
from property_street_backend.log_config.logger_config import (
    log_message
)
from property_street_backend.config.websocket_factory import (
    authenticated_ws,
    agents_ws,
    unauthenticated_ws,
)
from .schemas import SocketInitializerKwargsSchema
from property_street_backend.app.controllers.chat.store import handle_chat
from property_street_backend.app.controllers.asset_request.utils import asset_request_channel_handler
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
    independent of each user

    Args:
        websocket (WebSocket): client's websocket
        client_id (int): client_id if authenticated
        redis_client (Redis): redis instance
        is_agent (bool): boolean to indicate if user's an agent if authenticated
        db (AsynSession): postgres instance
    
    Optional Keyword Args:
        last_n_timestamp (int): Timestamp of the last notification the client/client socket received 
    """
    # add the websocket to the connected_ws dict
    # else add to the unauthenticated_ws set
    if client_id:
        authenticated_ws[client_id] = websocket
        # check the client is an agent and add the websocket to the connnected_agents_ws dict
        if is_agent:
            agents_ws[client_id] = websocket
    else:
        unauthenticated_ws.add(websocket)

    # register channels
    await register_channels(redis_client)

    # handle pending transactions
    asyncio.create_task(handle_pending_trx(
        user_id=client_id,
        redis_client=redis_client,
        ws=websocket,
        last_n_timestamp = kwargs.pop('last_timestamp',None),
        is_agent = is_agent,
        db = db
    ))

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

        # take off the websocket object from the connected_websockets and connected_agent_websocket dict
        if client_id:
            authenticated_ws.pop(client_id, None)
            if is_agent:
                agents_ws.pop(websocket,None)
        else:
            unauthenticated_ws.discard(websocket)

        if DEBUG:
            websocket_logger.error(f"Client disconnected", exc_info=True)
    
    finally:
        pass


async def register_channels(redis_client: Redis):
    pubsub = redis_client.pubsub()
    pubsub.subscribe(**{
        'asset-request-channel': asset_request_channel_handler
    })


async def ws_reception_handler(
    data: str,
    redis_client: Redis,
):
    loaded_data = json.loads(data)
    data_category = loaded_data.get('category',None)

    if data_category == 'chat':
        handle_chat(
            data = loaded_data,
            redis_client = redis_client,
            chat_lazy_offload_schedule = None
        )


async def handle_pending_trx(
    redis_client: Redis,
    user_id: int,
    db: AsyncSession,
    last_n_timestamp: int,
    is_agent: bool,
    ws: WebSocket
):
    # dispatch pending notification
    await dispatch_pending_notification(
        last_timestamp=last_n_timestamp,
        redis_client = redis_client,
        db = db,
        is_agent = is_agent,
        ws = ws,
        user_id = user_id
    )

    # dispatch pending chat
    await dispatch_pending_chat(
        redis_client = redis_client,
        user_id = user_id,
        db = db
    )