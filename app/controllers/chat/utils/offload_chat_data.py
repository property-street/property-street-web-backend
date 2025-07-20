import json
from datetime import datetime, timezone
from redis.asyncio import Redis
from sqlalchemy.sql import update, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Message, Thread
from .store import get_chat_next_offload_schedule
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
):
    """Items in the `chat_object` field of hset key created from `min_id` and `max_id` is offloaded to the database

    Args:
        redis_client (Redis): redis instance
        db (AsyncSession): database instance
        min_id (int): minimum id between the sender's and receiver
        max_id (int): maximum id between the sender's and receiver
        chat_lazy_offload_schedule (int): a timestamp which tells when the hset should be lazily offloaded

    Raises:
        e: _description_

    Returns:
        None: None
    """
    chat_lazy_offload_schedule = get_chat_next_offload_schedule()
    dialogue_key = f'chat_{min_id}_{max_id}'
    lock_key = f"offloading:{dialogue_key}"
    if not await acquire_redis_lock(redis_client, lock_key, ex = chat_lazy_offload_schedule):
        return  # Another offload in progress

    chat_obj = await redis_client.hget(dialogue_key, "chat_object")
    if not chat_obj:
        await release_redis_lock(redis_client,lock_key)
        return  # Nothing to offload

    # Optimistically delete to avoid race conditions
    await redis_client.hdel(dialogue_key, 'chat_object')

    try:
        # Get the thread ID (or create it)
        thread_id = await get_or_create_thread_id(min_id, max_id, db)

        # Load and prepare chat data
        loaded_chat_obj: dict = json.loads(chat_obj)
        update_data = []
        create_data = []

        for timestamp, item in loaded_chat_obj.items():
            item: dict
            if item.get('id'):
                update_data.append({
                    'id': item['id'],
                    'fmt_msg': item['fmt_msg'],
                    'status': item['status'],
                    'server_timestamp_ms': int(timestamp),
                })
            else:
                create_data.append({
                    'recipient_id': item['recipient_id'],
                    'sender_id': item['sender_id'],
                    'server_timestamp_ms': int(timestamp),
                    'fmt_msg': item['fmt_msg'],
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
                    fmt_msg=data['fmt_msg'],
                    server_timestamp_ms=data['server_timestamp_ms'],
                    status=data['status'],
                )
            )
            await db.execute(stmt)

        await db.commit()

        # Add db_id and thread_id to the offloaded object
        for msg in messages:
            ts = str(msg.server_timestamp_ms)
            if ts in loaded_chat_obj:
                loaded_chat_obj[ts]['id'] = msg.id
                loaded_chat_obj[ts]['thread_id'] = thread_id

        # Final Redis updates
        await redis_client.hset(dialogue_key, mapping={
            'offloaded': json.dumps(loaded_chat_obj),
            'lazy_timestamp': chat_lazy_offload_schedule,
        })
        await redis_client.hdel(dialogue_key, 'offloading')

    except Exception as e:
        # On failure, return chat object 
        await redis_client.hset(dialogue_key, 'chat_object', chat_obj)
        raise e  # Optionally re-raise or log

    finally:
        await redis_client.delete(lock_key)