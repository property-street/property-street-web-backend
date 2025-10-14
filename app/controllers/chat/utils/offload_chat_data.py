import json
from typing import List
from datetime import datetime, timezone
from redis.asyncio import Redis
from sqlalchemy.sql import update, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Message, Thread
from .store import (
    get_pending_messages,
    get_chat_next_offload_schedule,
)
from ..schemas import CachedMessageSchema
from property_street_backend.app.models import User
from property_street_backend.app.initiator import logger
from property_street_backend.config.settings import DEBUG
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

    
    stmt = select(User).where(User.id.in_([min_id, max_id]))
    result = await db.execute(stmt)
    users = result.scalars().all()

    if not thread:
        thread = Thread(participants=[*users])
        db.add(thread)
        await db.commit()
        await db.refresh(thread)

    return thread.id



async def offload_dialogue(
    *,
    redis_client: Redis,
    db: AsyncSession,
    dialogue_key: str,
):
    """
    Offloads cached chat messages between two users from Redis to the database.

    Args:
        redis_client (Redis): Redis client instance.
        db (AsyncSession): SQLAlchemy database session.
        min_id (int): Lower user ID (sorted).
        max_id (int): Higher user ID (sorted).
    """
    split_key = dialogue_key.split('_')
    min_id: int = int(split_key[1])
    max_id: int = int(split_key[2])
    chat_lazy_offload_schedule = get_chat_next_offload_schedule()
    dialogue_key = f'chat_{min_id}_{max_id}'
    lock_key = f"offloading:{dialogue_key}"

    if DEBUG:
        logger.info(f"[Offload] Starting offload for {dialogue_key}")

    if not await acquire_redis_lock(redis_client, lock_key, ex=chat_lazy_offload_schedule):
        if DEBUG:
            logger.info(f"[Offload] Skipped due to existing lock for {dialogue_key}")
        return

    try:
        cached_messages: dict[str, CachedMessageSchema] = await get_pending_messages(redis_client,dialogue_key)
        if not cached_messages:
            if DEBUG:
                logger.info(f"[Offload] No messages to offload for {dialogue_key}")
            return

        # Optimistically remove messages from Redis to prevent race overwrite
        await redis_client.hdel(dialogue_key, "messages")

        thread_id = await get_or_create_thread_id(db, min_id, max_id)

        new_messages: List[Message] = []
        updated_messages_count = 0

        for timestamp, item in cached_messages.items():
            item: dict
            if not item.get("id"):
                new_messages.append(
                    Message(
                        sender_id=item["sender_id"],
                        recipient_id=item["recipient_id"],
                        fmt_msg=item["fmt_msg"],
                        status=item["status"],
                        msg_type=item["msg_type"],
                        thread_id=thread_id,
                        server_timestamp_ms=float(timestamp),
                    )
                )
            else:
                stmt = (
                    update(Message)
                    .where(Message.id == item["id"])
                    .values(
                        fmt_msg=item["fmt_msg"],
                        status=item["status"],
                        msg_type=item["msg_type"],
                    )
                )
                await db.execute(stmt)
                updated_messages_count += 1

        # add new messages to session
        if new_messages:
            db.add_all(new_messages)

        await db.commit()

        if DEBUG:
            logger.info(
                f"[Offload] Completed for {dialogue_key}. Inserted: {len(new_messages)}, Updated: {updated_messages_count}"
            )

        # Clean up Redis if no one has added anything since we offloaded
        current_chat_obj: dict[str, CachedMessageSchema] = await get_pending_messages(redis_client,dialogue_key)
        if not current_chat_obj:
            await redis_client.delete(dialogue_key)
            if DEBUG:
                logger.info(f"[Offload] Redis key {dialogue_key} deleted after final check")

    except Exception as e:
        # Restore chat object into Redis for retry
        await redis_client.hset(dialogue_key, "messages", cached_messages)
        if DEBUG:
            logger.error(f"[Offload] Error while offloading {dialogue_key}: {e}", exc_info=True)

        # Optional: Send to error monitor (Sentry, etc.)
        # monitor.capture_exception(e)

        raise

    finally:
        await release_redis_lock(redis_client,lock_key)
        logger.info(f"[Offload] Lock released for {dialogue_key}")