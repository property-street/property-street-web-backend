import time
import json
from fastapi import WebSocket
from redis.asyncio import Redis

from property_street_backend.config.settings import DEBUG
from property_street_backend.app.controllers.ws_init import websocket_logger
from property_street_backend.app.controllers.ws_init import agent_pend_pool_key

async def pubsub_request_handler(websocket:WebSocket, parsed_data:dict, redis_client: Redis):
    if DEBUG:
        websocket_logger.info('**pubsub_request_handler invoked')

    unix_timestamp_ms = int(time.time()*1000)
    await redis_client.zadd(
        agent_pend_pool_key, 
        {json.dumps(parsed_data): unix_timestamp_ms}
    )

    # send the message
    try:
        if websocket:
            await websocket.send_json({
                'event': 'asset_request',
                'data': parsed_data
            })
            if DEBUG:
                websocket_logger.info(f"Message sent successfully to receiver!")
        else: 
            if DEBUG:
                websocket_logger.info(f"Instance's socket disconnected at the moment!")
            raise ConnectionError
    except Exception as e:
        pass