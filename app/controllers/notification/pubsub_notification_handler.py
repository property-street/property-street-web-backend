from fastapi import WebSocket

from property_street_backend.config.settings import DEBUG
from property_street_backend.app.controllers.ws_init import websocket_logger, channel_categories

async def pubsub_notification_handler(websocket: WebSocket, data: dict):
    if DEBUG:
        websocket_logger.info('**pubsub_request_handler invoked')

    try:
        if websocket:
            cat = channel_categories['notification']
            await websocket.send_json({
                'event': {
                    'class': cat,
                    'category': cat,
                },
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