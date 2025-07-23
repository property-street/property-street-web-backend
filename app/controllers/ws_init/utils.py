from functools import wraps
from fastapi import WebSocket
from redis.asyncio import Redis
from sqlalchemy.orm import sessionmaker
from fastapi import WebSocketException, status

from property_street_backend.app.database import get_db
from property_street_backend.app.initiator import logger
from property_street_backend.config.settings import DEBUG
from property_street_backend.app.controllers.ws_init import aa_actors_set_key, websocket_logger
from property_street_backend.app.controllers.notification.utils import dispatch_pending_notification
from property_street_backend.app.controllers.chat.dispatch_pending_chat import dispatch_pending_chat

async def handle_pending_trx(
    db_session_maker: sessionmaker,
    redis_client: Redis,
    user_id: int,
    last_n_timestamp: int,
    is_agent: bool,
    websocket: WebSocket
):
    async with db_session_maker() as db:
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
            db = db,
            websocket = websocket
        )


def require_user_online(redis_client: Redis):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, user_id: int, *args, **kwargs):
            is_online = await redis_client.sismember(aa_actors_set_key, user_id)
            if not is_online:
                msg = f"User {user_id} is offline."
                if DEBUG:
                    websocket_logger.info(msg)
                raise WebSocketException(
                    code = status.WS_1008_POLICY_VIOLATION,
                    reason = msg
                )
            return await func(self, user_id, *args, **kwargs)
        return wrapper
    return decorator