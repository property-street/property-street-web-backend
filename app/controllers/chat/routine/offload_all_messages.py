import json
from sqlalchemy import select, update
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import Thread, User, Message

async def offload_messages(
    redis_client: Redis,
    sender_id: int,
    recipient_id: int,
    db: AsyncSession,
):
    key = f"msg_to_offload:{min(sender_id, recipient_id)}:{max(sender_id, recipient_id)}"
    order_key = f"{key}:order"

    # Step 1: Fetch all cached messages in order
    fields = await redis_client.lrange(order_key, 0, -1)
    if not fields:
        return  # No messages to offload

    messages = [json.loads(await redis_client.hget(key, field)) for field in fields]

    # Step 2: Fetch or create the Thread
    thread_stmt = (
        select(Thread)
        .where(
            (Thread.participants.any(User.id == sender_id))
            & (Thread.participants.any(User.id == recipient_id))
        )
    )
    thread_result = await db.execute(thread_stmt)
    thread = thread_result.scalars().first()

    if not thread:
        thread = Thread(participants=[sender_id, recipient_id])
        db.add(thread)
        await db.commit()
        await db.refresh(thread)

    # Step 3: Prepare messages for bulk operations
    new_messages = []
    update_operations = []

    for message in messages:
        if "db_id" in message:
            # Existing message, update fields
            update_stmt = (
                update(Message)
                .where(Message.id == message["db_id"])
                .values(
                    text_content=message["text_content"],
                    updated_timestamp=message["updated_timestamp"],
                    status=message["status"],
                )
            )
            update_operations.append(update_stmt)
        else:
            # New message, create instance
            new_message = Message(
                thread_id=thread.id,
                sender_id=message["sender_id"],
                recipient_id=message["recipient_id"],
                content=message["content"],
                created_at=message["timestamp"],
                status=message["status"],
            )
            new_messages.append(new_message)

    # Step 4: Execute bulk operations
    if new_messages:
        db.add_all(new_messages)
    for stmt in update_operations:
        await db.execute(stmt)

    await db.commit()

    # Step 5: Cleanup Redis
    await redis_client.delete(key)
    await redis_client.delete(order_key)
