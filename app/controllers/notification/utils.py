import json
from fastapi import WebSocket
from redis.asyncio import Redis
from sqlalchemy import select, desc, update
from sqlalchemy.ext.asyncio import AsyncSession


from property_street_backend.app.initiator import logger
from property_street_backend.config.settings import DEBUG
from property_street_backend.app.models import Notification
from property_street_backend.app.controllers.ws_init import (
    websocket_logger,
    user_pend_pool_key, 
    agent_pend_pool_key, 
    user_pend_pool_fields,
    add_pending_tokens_to_user_pool, 
)
from property_street_backend.log_config.logger_config import log_message


async def dispatch_pending_notification(
    *,
    last_timestamp: int,
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
        logger.info('*In dispatch_pending_notification function*')
    # Try retrieving the last known timestamp from the database if not provided
    if not last_timestamp:
        result = await db.execute(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(desc(Notification.created_at))
            .limit(1)
        )
        last_db_entry = result.scalar_one_or_none()
        if last_db_entry:
            last_timestamp = last_db_entry.created_at

    if last_timestamp:
        # === Agent Lazy Notifications (ZSET) ===
        if is_agent:
            lazy_notifications = await redis_client.zrangebyscore(
                agent_pend_pool_key, min = last_timestamp + 1, max ="+inf"
            )
            if lazy_notifications:
                await ws.send_json({
                    'event': 'agent_pending_lazy_notifications',
                    'data': [json.loads(obj) for obj in lazy_notifications]
                })
                msg = f"Successfully pinged pending lazy agent messages to user id {user_id}"
                if DEBUG:
                    websocket_logger.info(f"**{msg}")
    # === No timestamp + Agent fallback ===
    elif is_agent:
        entries = await redis_client.zrange(agent_pend_pool_key, 0, -1)
        if entries:
            await ws.send_json({
                'event': 'agent_pending_lazy_notifications',
                'data': [json.loads(obj) for obj in entries]
            })
            msg = f"Successfully pinged pending lazy agent notification to agent with user_id {user_id}"
            if DEBUG:
                websocket_logger.info(f"**{msg}")
    
    # === User DB-based Notifications (HSET of notification IDs) ===
    _user_pend_pool_key = user_pend_pool_key(user_id)
    pending_ids_field = user_pend_pool_fields['notification']
    pending_notification_data = await redis_client.hget(_user_pend_pool_key, pending_ids_field)

    if pending_notification_data:
        try:
            loaded_ids = json.loads(pending_notification_data)
        except json.JSONDecodeError:
            log_message('error', "Error 'json-desearializing' pending notification for user {user_id}")
            loaded_ids = []

        if isinstance(loaded_ids, list) and loaded_ids:
            stmt = select(Notification).where(Notification.id.in_(loaded_ids))
            result = await db.execute(stmt)
            notifications = result.scalars().all()

            if notifications:
                await ws.send_json({
                    'event': 'pending_notification',
                    'data': [
                        {
                            'category': 'notification',
                            'timestamp': inst.created_at,
                            'db_id': inst.id,
                            'content': inst.n_serialized_obj
                        } for inst in notifications
                    ]
                })
                msg = f"Successfully pinged pending notifications to user_id {user_id}"
                if DEBUG:
                    websocket_logger.info(f"**{msg}")

                # Mark as delivered in DB
                for inst in notifications:
                    stmt = (
                        update(Notification)
                        .where(Notification.id == inst.id)
                        .values(n_status='delivered')
                    )
                    await db.execute(stmt)

                await db.commit()
                await redis_client.hdel(_user_pend_pool_key, pending_ids_field)


async def add_pending_notification_token_to_user_pool(
    notification_id: int,
    redis_client: Redis,
    client_id: int,        
):
    await add_pending_tokens_to_user_pool(
        user_id=client_id, 
        token=notification_id, 
        pool_field=user_pend_pool_fields['notification'], 
        redis_client=redis_client,
    )