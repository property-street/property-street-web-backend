from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload


from .get_threads_schemas import (
    ThreadSummarySchema, 
    MessageSummarySchema
)
from property_street_backend.app.models import User, Thread, Message


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
            func.max(Message.server_timestamp_ms).label("latest_timestamp")
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
                LatestMessage.server_timestamp_ms == latest_message_subq.c.latest_timestamp
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


async def get_messages(
    db: AsyncSession,
    host_id: int,
    participant_id: int,
    page: int = 1,
    size: int = 100
):
    thread_stmt = (
        select(Thread)
        .where(
            (Thread.participants.any(User.id == host_id)) &
            (Thread.participants.any(User.id == participant_id))
        )
    )
    thread_result = await db.execute(thread_stmt)
    thread = thread_result.scalars().first()

    if not thread:
        return []

    offset = (page - 1) * size

    message_stmt = (
        select(Message)
        .where(Message.thread_id == thread.id)
        .order_by(Message.server_timestamp_ms.desc())  # assuming `timestamp` or `created_at` field
        .limit(size)
        .offset(offset)
    )

    message_result = await db.execute(message_stmt)
    messages = message_result.scalars().all()

    return messages

    
