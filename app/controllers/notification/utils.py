import json
from fastapi import WebSocket
from redis.asyncio import Redis
from sqlalchemy import select, desc, update
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import Notification
from property_street_backend.app.controllers.ws_init import agent_pend_pool_key
from property_street_backend.app.controllers.ws_init import user_pend_pool_key

async def dispatch_pending_notification(
    *,
    last_timestamp: int,
    redis_client: Redis,
    db: AsyncSession,
    is_agent: bool,
    user_id: int,
    ws: WebSocket,
):
    """
    Dispatch pending notifications to an agent or user.
    Handles Redis zset for agents and hash-based notification IDs for users.
    Updates notification statuses and clears Redis fields accordingly.
    """

    # Try retrieving the last known timestamp from the database if not provided
    if not last_timestamp:
        result = await db.execute(
            select(Notification.timestamp)
            .where(Notification.user_id == user_id)
            .order_by(desc(Notification.timestamp))
            .limit(1)
        )
        last_db_entry = result.scalar_one_or_none()
        if last_db_entry:
            last_timestamp = last_db_entry.timestamp

    if last_timestamp:
        # === Agent Lazy Notifications (ZSET) ===
        if is_agent:
            lazy_notifications = await redis_client.zrangebyscore(
                agent_pend_pool_key, min=last_timestamp + 1, max="+inf"
            )
            if lazy_notifications:
                await ws.send_json({
                    'event': 'agent_pending_lazy_notifications',
                    'data': [json.loads(obj) for obj in lazy_notifications]
                })

        # === User DB-based Notifications (HSET of notification IDs) ===
        user_pend_pool_key = user_pend_pool_key(user_id)
        pending_ids_field = 'notifications'
        pending_data = await redis_client.hget(user_pend_pool_key, pending_ids_field)

        if pending_data:
            try:
                loaded_ids = json.loads(pending_data)
            except json.JSONDecodeError:
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
                                'timestamp': inst.timestamp,
                                'db_id': inst.id
                            } for inst in notifications
                        ]
                    })

                    # Mark as delivered in DB
                    for inst in notifications:
                        stmt = (
                            update(Notification)
                            .where(Notification.id == inst.id)
                            .values(n_status='delivered')
                        )
                        await db.execute(stmt)

                    await db.commit()
                    await redis_client.hdel(user_pend_pool_key, pending_ids_field)

    # === No timestamp + Agent fallback ===
    elif is_agent:
        entries = await redis_client.zrange(agent_pend_pool_key, 0, -1)
        if entries:
            await ws.send_json({
                'event': 'agent_pending_lazy_notifications',
                'data': [json.loads(obj) for obj in entries]
            })
