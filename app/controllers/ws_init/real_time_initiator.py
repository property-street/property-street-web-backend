import json
import asyncio
import logging
from fastapi import (
    WebSocket, 
    WebSocketDisconnect, 
)
import redis.asyncio as redis


from property_street_backend.config.settings import DEBUG
from property_street_backend.log_config.logger_config import (
    log_message
)
from property_street_backend.app.controllers.chat.utils import handle_chat
from property_street_backend.config.websocket_factory import (
    connected_ws,
    connected_agents_ws,
    unauthenticated_ws,
)


websocket_logger = logging.getLogger("websocket")


async def websocket_endpoint(
    websocket: WebSocket, 
    client_id: int,
    is_agent: True, 
    redis_client: redis.Redis,
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
    
    
    # create a pubsub object
    pubsub = redis_client.pubsub()

    try:
        # Subscribe to a client_id channel.
        await pubsub.subscribe(str(client_id))
       
        # Runs continuously in the background, 
        # fetching messages from the Redis Pub/Sub channel 
        channel_listener_task = asyncio.create_task(channel_recipient(
            websocket=websocket,
            redis_client=redis_client,
            pubsub=pubsub,
        ))

        await channel_listener_task # Keep task alive


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
        await pubsub.unsubscribe(client_id)
        channel_listener_task.cancel()

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


async def channel_recipient(
    websocket: WebSocket,
    redis_client: redis.Redis,
    pubsub: redis.client.PubSub,
): # pubsub channel recipient
    """Listens to a messge on a channel

    Args:
        pubsub (redis.client.PubSub): _description_
        websocket (WebSocket): _description_
        redis_client (redis.Redis): _description_
    """
    while True:
        message = await pubsub.get_message(ignore_subscribe_messages=True) # Read a message

        if message:
            message_obj = json.loads(message['data'].decode('utf-8'))
            msg_category = message_obj['data']['category']

            if msg_category == 'chat':
                handle_chat(
                    chat_obj=message_obj,
                    websocket=websocket,
                    redis_client=redis_client
                )

        await asyncio.sleep(0.01)


async def ws_reception_handler(
    data: str,
    redis_client: redis.Redis,
):
    loaded_data = json.loads(data)
    data_category = loaded_data.get('category',None)

    if data_category == 'chat':
        handle_chat(
            data = loaded_data,
            redis_client = redis_client,
            chat_lazy_offload_schedule = None
        )

async def publish_to_channel(
    data: dict,
    redis_client: redis.Redis,
):
    loaded_data = json.loads(data)
    await redis_client.publish('channel_name', data)