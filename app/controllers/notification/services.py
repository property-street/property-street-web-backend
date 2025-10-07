from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Notification

async def get_all_notification(db:AsyncSession, user_id: int):
    query = await db.execute(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.timestamp.desc())
    )
    return query.scalars().all()