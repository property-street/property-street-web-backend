import json
from redis.asyncio import Redis

from property_street_backend.app.controllers.ws_init import (
    user_pend_pool_key,
    user_pend_pool_fields,
)


async def get_pending_notification_ids(client_id: int, redis_client: Redis):
    pool_key = user_pend_pool_key(client_id)
    data = await redis_client.hget(pool_key, user_pend_pool_fields['notification'])
    return (json.loads(data) if data else [])