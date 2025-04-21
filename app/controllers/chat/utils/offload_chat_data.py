import json
from datetime import datetime, timezone, timedelta
from redis.asyncio import Redis
from sqlalchemy.sql import update, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Message, Thread
from property_street_backend.app.models import User
from property_street_backend.config.context_sessions import (
    acquire_redis_lock,
    release_redis_lock,
)


async def get_or_create_thread_id(db: AsyncSession, min_id: int, max_id: int) -> int:
    """gets or creates a thread id for the sender and recipient's id

    Args:
        db (AsyncSession): postgres sessio
        sender_id (int): sender id
        recipient_id (int): recipient id

    Returns:
        int: thread id
    """
    thread_stmt = (
        select(Thread)
        .where(
            (Thread.participants.any(User.id == min_id))
            & (Thread.participants.any(User.id == max_id))
        )
    )
    thread_result = await db.execute(thread_stmt)
    thread = thread_result.scalars().first()

    if not thread:
        thread = Thread(participants=[min_id, max_id])
        db.add(thread)
        await db.commit()
        await db.refresh(thread)

    return thread.id


async def offload_chat_data(
    *,
    redis_client: Redis,
    db: AsyncSession,
    min_id: int,
    max_id: int,
    chat_lazy_offload_schedule: int,
):
    chat_key = f'chat_{min_id}_{max_id}'
    lock_key = f"offloading:{chat_key}"
    if not await acquire_redis_lock(redis_client, lock_key, ex = chat_lazy_offload_schedule):
        return  # Another offload in progress

    chat_obj = await redis_client.hget(chat_key, "chat_object")
    if not chat_obj:
        await release_redis_lock(redis_client,lock_key)
        return  # Nothing to offload

    # Optimistically delete to avoid race conditions
    await redis_client.hdel(chat_key, 'chat_object')

    try:
        # Get the thread ID (or create it)
        thread_id = await get_or_create_thread_id(min_id, max_id, db)

        # Load and prepare chat data
        loaded_chat_obj = json.loads(chat_obj)
        update_data = []
        create_data = []

        for timestamp, item in loaded_chat_obj.items():
            if item.get('db_id'):
                update_data.append({
                    'id': item['db_id'],
                    'text_content': item['fmt_msg_txt'],
                    'status': item['status'],
                    'timestamp': int(timestamp),
                })
            else:
                create_data.append({
                    'recipient_id': item['recipient_id'],
                    'sender_id': item['sender_id'],
                    'timestamp': int(timestamp),
                    'text_content': item['fmt_msg_txt'],
                    'status': item['status'],
                    'thread_id': thread_id,
                })

        # Insert new messages
        messages = []
        if create_data:
            messages = [Message(**data) for data in create_data]
            db.add_all(messages)
            await db.flush()  # Required to get assigned IDs

        # Update existing messages
        for data in update_data:
            stmt = (
                update(Message)
                .where(Message.id == data['id'])
                .values(
                    text_content=data['text_content'],
                    created_at=datetime.fromtimestamp(data['timestamp'], tz=timezone.utc),
                    status=data['status'],
                )
            )
            await db.execute(stmt)

        await db.commit()

        # Add db_id and thread_id to the offloaded object
        for msg in messages:
            ts = str(msg.timestamp)
            if ts in loaded_chat_obj:
                loaded_chat_obj[ts]['db_id'] = msg.id
                loaded_chat_obj[ts]['thread_id'] = thread_id

        # Final Redis updates
        lazy_timestamp = datetime.now(timezone.utc) + timedelta(seconds=chat_lazy_offload_schedule)
        await redis_client.hset(chat_key, mapping={
            'offloaded': json.dumps(loaded_chat_obj),
            'lazy_timestamp': int(lazy_timestamp.timestamp()),
        })
        await redis_client.hdel(chat_key, 'offloading')

    except Exception as e:
        # On failure, return chat object to Redis
        await redis_client.hset(chat_key, 'chat_object', chat_obj)
        raise e  # Optionally re-raise or log

    finally:
        await redis_client.delete(lock_key)