from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload


from .models import Thread, Message
from property_street_backend.app.models import User
from .get_threads_schemas import (
    ThreadSummarySchema, 
    MessageSummarySchema
)


async def get_threads_with_latest_message(
    db: AsyncSession,
    user_id: int,
    page: int = 1,
    page_size: int = 100
):

    # Step 1: Subquery to find latest message timestamp per thread
    latest_message_subq = (
        select(
            Message.thread_id,
            func.max(Message.timestamp).label("latest_timestamp")
        )
        .group_by(Message.thread_id)
        .subquery()
    )

    # Step 2: Alias the Message table to join the actual latest message
    LatestMessage = aliased(Message)

    # Step 3: Query threads where the user is a participant
    stmt = (
        select(Thread, LatestMessage)
        .join(Thread.participants)  # assuming Thread.participants is set up
        .outerjoin(
            latest_message_subq,
            Thread.id == latest_message_subq.c.thread_id
        )
        .outerjoin(
            LatestMessage,
            and_(
                LatestMessage.thread_id == latest_message_subq.c.thread_id,
                LatestMessage.timestamp == latest_message_subq.c.latest_timestamp
            )
        )
        .options(
            selectinload(LatestMessage.sender).selectinload(User.profile_avatar),
            selectinload(LatestMessage.recipient).selectinload(User.profile_avatar)
        )
        .where(User.id == user_id)
        .order_by(Thread.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    result = await db.execute(stmt)
    rows = result.all()
    
    return [
        ThreadSummarySchema(
            id=thread.id,
            created_at=thread.created_at,
            last_message=MessageSummarySchema.model_validate(last_msg) if last_msg else None
        )
        for thread, last_msg in rows
    ]

"""
Thread       Latest Message Subquery       Message (Alias)
------       -----------------------       ----------------
id   ----->  thread_id                    thread_id
            latest_timestamp   ------>    timestamp

"""