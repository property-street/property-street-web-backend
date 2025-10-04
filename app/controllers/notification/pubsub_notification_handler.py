from fastapi import WebSocket
from redis.asyncio import Redis

from .schemas import NotificationResponse
from property_street_backend.config.settings import DEBUG
from .utils import add_pending_notification_token_to_user_pool
from property_street_backend.app.controllers.ws_init import websocket_logger, channel_categories

async def pubsub_notification_handler(websocket: WebSocket, data: NotificationResponse, redis_client: Redis):
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
        recipient_id = data['user_id']
        await add_pending_notification_token_to_user_pool(
            notification_id=data['id'],
            redis_client = redis_client,
            client_id = recipient_id,
        )
        if DEBUG:
            websocket_logger.info(f"Error while sending notification to user {recipient_id}! Reason: {e}")
        raise e