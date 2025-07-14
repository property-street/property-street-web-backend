import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import Thread, Message
from property_street_backend.app.controllers.auth.services import fetched_access_token
from property_street_backend.tests.auth.test_user_creation import create_test_user
from property_street_backend.app.schemas.auth_schemas import UserRegistrationSchema
from property_street_backend.app.controllers.chat.services import get_threads_with_latest_message  
from property_street_backend.app.controllers.chat.get_threads_schemas import (
    ThreadSummarySchema,
)



@pytest.mark.asyncio
async def test_get_threads_with_latest_message(client__fixture):
    async for fixture_obj in client__fixture:
        test_db: AsyncSession = fixture_obj['db']
        httpx_client: AsyncClient = fixture_obj['http_client']
        break

    # Create test users
    user1 = await create_test_user(test_db)
    user2 = await create_test_user(test_db, UserRegistrationSchema(
        username='partner',
        email='partner@example.com',
        password='securepass',
        first_name="secure",
        last_name="pass"
    ))

    token = fetched_access_token(user1)['access_token']
    headers = {"Authorization": f"Bearer {token}"}

    # Create multiple threads between them
    threads = []
    for i in range(3):
        messages = [
            Message(
                text_content=f"Thread {i} - Message {j}",
                timestamp=j,
                status="sent",
                sender_id=user1.id if j % 2 == 0 else user2.id,
                recipient_id=user2.id if j % 2 == 0 else user1.id
            ) for j in range(5)  # 5 messages per thread
        ]

        thread = Thread(
            messages=messages,
            participants=[user1, user2]
        )
        threads.append(thread)

    test_db.add_all(threads)
    await test_db.commit()

    # Fetch threads for user1
    response = await httpx_client.get(
        '/chat/get_threads_meta',
        headers = headers,
    )
    results = response.json()


    # Verify structure and correctness
    assert len(results) == 3
    for thread_data in results:
        ThreadSummarySchema.model_validate(thread_data)