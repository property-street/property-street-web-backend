import json
import logging
from fastapi import (
    WebSocket, 
    WebSocketDisconnect, 
)
from redis.asyncio import Redis, client


from property_street_backend.config.settings import DEBUG
from property_street_backend.log_config.logger_config import (
    log_message
)
from property_street_backend.config.websocket_factory import (
    connected_ws,
    connected_agents_ws,
    unauthenticated_ws,
)
from property_street_backend.app.controllers.chat.utils import handle_chat
from property_street_backend.app.controllers.asset_request.utils import asset_request_chanel_handler


websocket_logger = logging.getLogger("websocket")


async def websocket_endpoint(
    websocket: WebSocket, 
    client_id: int,
    is_agent: True, 
    redis_client: Redis,
):
    """websocket endpoint handler for real time functionality of the application
    independent of each user

    Args:
        websocket (WebSocket): _description_
        client_id (int): _description_
        redis_client (redis.Redis): _description_
    """
    await websocket.accept()

    # add the websocket to the connected_ws dict
    # else add to the unauthenticated_ws set
    if client_id:
        connected_ws[client_id] = websocket
        # check the client is an agent and add the websocket to the connnected_agents_ws dict
        if is_agent:
            connected_agents_ws[client_id] = websocket
    else:
        unauthenticated_ws.add(websocket)

    # register channels
    await register_channels(redis_client)

    # handle pending notifications

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
            connected_ws.pop(websocket, None)
            if is_agent:
                connected_agents_ws.pop(websocket,None)
        else:
            unauthenticated_ws.discard(websocket)

        if DEBUG:
            websocket_logger.error(f"Client disconnected", exc_info=True)
    
    finally:
        pass
        # handle pending transactions
        # await handle_pending_trx(
        #     client_id=client_id,
        #     redis_client=redis_client,
        #     websocket=websocket,
        # )


async def register_channels(redis_client: Redis):
    pubsub = redis_client.pubsub()
    pubsub.subscribe(**{
        'asset-request-channel': asset_request_chanel_handler
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


async def handle_pending_trx():
    # handle pending notification
    pass