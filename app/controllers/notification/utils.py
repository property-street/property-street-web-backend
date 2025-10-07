import json
from datetime import datetime
from fastapi import WebSocket
from typing import List, Union
from redis.asyncio import Redis
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import select, desc, update
from sqlalchemy.ext.asyncio import AsyncSession


from .schemas import NotificationResponse
from . import get_pending_notification_ids
from property_street_backend.app.initiator import logger
from property_street_backend.config.settings import DEBUG
from property_street_backend.app.models import Notification
from property_street_backend.app.controllers.ws_init import (
    pong_class,
    websocket_logger,
    user_pend_pool_key, 
    agent_pend_pool_key, 
    user_pend_pool_fields,
    get_timestamp_milliseconds,
    add_pending_tokens_to_user_pool, 
)
from property_street_backend.log_config.logger_config import log_message


def organize_payload(o_list: List[Union[str, Notification]]) -> dict:
    return [
        {
            **(NotificationResponse.model_validate(
                json.loads(inst) if isinstance(inst,str|bytes) else inst
            ).model_dump()),
        } for inst in o_list
    ] if o_list else []


def bump_decimal(score) -> str:
    """
    score: str, bytes, float or Decimal
    returns: bumped score as string (one least-decimal-place higher)
    """
    # get stable string representation
    if isinstance(score, bytes):
        s = score.decode()
    elif isinstance(score, float):
        s = format(score, ".17g")   # preserves full float digits reliably
    else:
        s = str(score)

    dec = Decimal(s)                   # exact decimal from the textual representation
    exp = dec.as_tuple().exponent      # negative if there are fractional digits
    precision = -exp if exp < 0 else 0
    increment = Decimal(1).scaleb(-precision)  # 1e-precision, or 1 if precision==0
    bumped = (dec + increment).quantize(increment)  # keep same scale
    return format(bumped)  # string, safe to pass to Redis

def zrangemin(last_timestamp_ms):
    # last_timestamp_ms may be float or str/bytes from Redis
    return ( format(last_timestamp_ms, ".17g")   # stable text form of the float
        if isinstance(last_timestamp_ms, float)
        else last_timestamp_ms.decode() if isinstance(last_timestamp_ms, bytes) else str(last_timestamp_ms)
    )

async def dispatch_pending_notification(
    *,
    last_timestamp_ms: float,
    redis_client: Redis,
    is_agent: bool,
    user_id: int,
    ws: WebSocket,
    db: AsyncSession,
):
    """
    Dispatch pending notifications to an agent or user.
    Handles Redis zset for agents and hash-based notification IDs for users.
    Updates notification statuses and clears Redis fields accordingly.
    """
    if DEBUG:
        logger.info('**In dispatch_pending_notification function*')
    # === Try retrieving the last known timestamp from the database if not provided
    if not last_timestamp_ms:
        result = await db.execute(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(desc(Notification.timestamp))
            .limit(1)
        )
        last_db_entry = result.scalar_one_or_none()
        if last_db_entry:
            last_timestamp_ms: float = last_db_entry.timestamp

    results = []
    # === Agent ZSET-based Notification
    if is_agent:
        # === Agent Lazy Notifications (ZSET) ===
        if last_timestamp_ms:
            bumped_timestamp: float = bump_decimal(last_timestamp_ms)
            if DEBUG:
                websocket_logger.info(f"bumped_timestamp: {bumped_timestamp}")
            lazy_notifications: List = await redis_client.zrangebyscore(
                agent_pend_pool_key, min = bumped_timestamp, max ="+inf"
            )
            if lazy_notifications:
                results.extend(organize_payload(lazy_notifications))
        # === No timestamp + Agent fallback ===
        else:
            entries: List = await redis_client.zrange(agent_pend_pool_key, 0, -1)
            if entries:
                results.extend(organize_payload(entries))

    # === User DB-based Notifications (HSET of notification IDs) ===
    loaded_ids: List[int] = await get_pending_notification_ids(user_id, redis_client)
    if loaded_ids:
        stmt = select(Notification).where(Notification.id.in_(loaded_ids))
        result = await db.execute(stmt)
        notifications = result.scalars().all()

        if notifications:
            results.extend(organize_payload(notifications))
            if DEBUG:
                msg = f"Successfully pinged {len(notifications)} pending notifications to user_id {user_id}"
                websocket_logger.info(msg)

            new_loaded_ids: List[int] = await get_pending_notification_ids(user_id, redis_client)
            await add_pending_notification_token_to_user_pool(
                new_loaded_ids[len(new_loaded_ids):], # sliced tokens excluding previous
                redis_client,
                user_id,
                replace=True
            )
    
    if results:
        await ws.send_json({
            'event': {
                'category': 'pending-notification',
                'class': pong_class['notification']
            },
            'data': results
        })


async def add_pending_notification_token_to_user_pool(
    notification_ids: int|List[int],
    redis_client: Redis,
    client_id: int,
    **kwargs
):
    """Caches Notifiation model ids to redis

    Args:
        notification_ids (int | List[int]): id(s) to be cached
        redis_client (Redis): redis instane
        client_id (int): user_id for identifying pool
        kwargs: 
            replace: bool = False: Determines if the pool should be replaced by the current input
    """
    await add_pending_tokens_to_user_pool(
        user_id=client_id, 
        tokens=notification_ids, 
        pool_field=user_pend_pool_fields['notification'], 
        redis_client=redis_client,
        **kwargs
    )