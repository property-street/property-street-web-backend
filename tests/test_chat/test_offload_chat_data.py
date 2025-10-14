import json
import pytest
from datetime import datetime
from sqlalchemy import select
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from . import message as message_template
from property_street_backend.app.models import User, Thread, Message
from property_street_backend.app.controllers.chat import chat_dialogue_hset_key
from property_street_backend.tests.auth.test_user_creation import create_test_user
from property_street_backend.app.schemas.auth_schemas import UserRegistrationSchema
from property_street_backend.app.controllers.chat.schemas import CachedMessageSchema
from property_street_backend.app.controllers.chat.utils.store import get_pending_messages
from property_street_backend.app.controllers.chat.utils.offload_chat_data import offload_dialogue


@pytest.mark.asyncio
async def test_offload_dialogue_creates_thread_and_persists_messages(client__fixture):
    """
    Validates that cached chat messages in Redis are correctly offloaded
    into the database, creating a thread if needed.
    """
    test_db: AsyncSession = client__fixture["db"]
    redis_client: Redis = client__fixture["redis_client"]

    sender = await create_test_user(test_db)
    recipient = await create_test_user(test_db, UserRegistrationSchema(
        username='recipient',
        email='recipient@example.com',
        password='strongpassword',
        first_name = 'recipient'
    ))
    sender_id = sender.id
    recipient_id = recipient.id

    dialogue_key = chat_dialogue_hset_key(sender.id, recipient.id)

    # STEP 2: Prepare a fake cached message
    server_ts: float = datetime.now().timestamp() * 1000
    cached_message : dict = CachedMessageSchema.model_validate({
        **message_template,
        "sender_id": sender_id,
        "recipient_id": recipient_id,
        "server_timestamp_ms": server_ts
    }).model_dump()

    # Store message in Redis under dialogue_key
    await redis_client.hset(dialogue_key, 'messages', json.dumps({server_ts: cached_message}))

    # Confirm Redis has it
    redis_data = await get_pending_messages(redis_client, dialogue_key)
    assert redis_data, "Cached message was not stored in Redis properly."

    # STEP 3: Run the offload
    await offload_dialogue(
        redis_client=redis_client,
        db=test_db,
        dialogue_key=dialogue_key
    )

    # STEP 4: Validate database persistence
    thread_stmt = select(Thread).where(
        (Thread.participants.any(User.id == sender_id)) &
        (Thread.participants.any(User.id == recipient_id))
    )
    thread_result = await test_db.execute(thread_stmt)
    thread = thread_result.scalars().first()
    assert thread, "Thread was not created during offload."

    msg_stmt = select(Message).where(Message.thread_id == thread.id)
    msg_result = await test_db.execute(msg_stmt)
    messages = msg_result.scalars().all()

    assert len(messages) == 1, "Expected exactly one message persisted."
    msg = messages[0]
    assert msg.sender_id == sender_id
    assert msg.recipient_id == recipient_id

    # STEP 5: Redis cleanup validation
    final_chat_obj = await get_pending_messages(redis_client, dialogue_key)
    assert not final_chat_obj, "Redis key should be cleaned after successful offload."

    # STEP 6: Idempotence test — running again shouldn't re-insert
    # await offload_dialogue(redis_client=redis_client, db=test_db, dialogue_key=dialogue_key)
    # msg_result2 = await test_db.execute(msg_stmt)
    # messages2 = msg_result2.scalars().all()
    # assert len(messages2) == 1, "Offload should not create duplicate messages."
