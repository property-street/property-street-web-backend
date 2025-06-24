import pytest
import random
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import Message, Thread
from property_street_backend.app.controllers.chat.core import get_messages
from property_street_backend.tests.auth.test_user_creation import create_test_user
from property_street_backend.app.schemas.auth_schemas import UserRegistrationSchema

@pytest.mark.asyncio
async def test_get_messages( get_test_db__fixture ):
    db = None
    try:
        async for test_db in get_test_db__fixture:
            test_db: AsyncSession
            break

        db = test_db
        sender = await create_test_user(test_db)
        recipient = await create_test_user(test_db, UserRegistrationSchema(
            username='recipient',
            email='recipient@example.com',
            password='strongpassword'
        ))
        messages = []
        for i in range(100):
            random_id = random.choice([sender.id, recipient.id])
            messages.append(
                Message(
                    text_content = f'Content{i+1}',
                    status="unsent",
                    timestamp=i*1000,
                    sender_id = random_id,
                    recipient_id = recipient.id if random_id is not recipient.id else sender.id 
                )
            )

        thread = Thread(
            messages = messages,
            participants = [sender,recipient]
        )
        test_db.add(thread)
        await test_db.commit()


        # get first page of messages
        page1 = 1
        page1_size = 20
        page1_messages = await get_messages(
            db = test_db,
            host_id = sender.id,
            participant_id = recipient.id,
            page = page1,
            page_size = page1_size
        )
        assert page1_messages[0].text_content == messages[-1].text_content
        assert page1_messages[-1].timestamp == messages[100-page1_size].timestamp

        # get second page of messages
        page2 = 2
        page2_size = 50
        page2_messages = await get_messages(
            db = test_db,
            host_id = sender.id,
            participant_id = recipient.id,
            page = page2,
            page_size = page2_size
        )
        assert page2_messages[0].text_content == messages[((page2-1) * page2_size)-1].text_content
        assert page2_messages[-1].timestamp == messages[0].timestamp
    finally:
        if db:
            await db.close()