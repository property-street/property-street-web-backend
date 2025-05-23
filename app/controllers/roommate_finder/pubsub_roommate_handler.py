import json
from fastapi import WebSocket

from property_street_backend.config.settings import DEBUG
from property_street_backend.app.controllers.ws_init import websocket_logger

async def pubsub_roommate_handler(websocket: WebSocket, data: dict):
    if DEBUG:
        websocket_logger.info('**pubsub_request_handler invoked')

    try:
        if websocket:
            await websocket.send_json({
                'event': data.get('category'),
                'data': data,
            })
            if DEBUG:
                websocket_logger.info(f"Message sent successfully to receiver!")
        else: 
            if DEBUG:
                websocket_logger.info(f"Instance's socket disconnected at the moment!")
            raise ConnectionError
    except Exception as e:
        raise e