from fastapi import WebSocket
from redis.asyncio import Redis

from property_street_backend.app.database import get_db
from property_street_backend.app.controllers.notification.utils import dispatch_pending_notification
from property_street_backend.app.controllers.chat.dispatch_pending_chat import dispatch_pending_chat

async def handle_pending_trx(
    redis_client: Redis,
    user_id: int,
    last_n_timestamp: int,
    is_agent: bool,
    websocket: WebSocket
):
    async for db in get_db():
        break

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
        # await dispatch_pending_chat(
        #     redis_client = redis_client,
        #     user_id = user_id,
        #     db = db,
        #     websocket = websocket
        # )
    pass