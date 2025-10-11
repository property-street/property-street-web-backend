import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from . import message as message_template, fmt_msg
from property_street_backend.app.controllers.chat.schemas import FMTMSG
from property_street_backend.app.models import Thread, Message, CloudImageDetail
from property_street_backend.tests.auth.test_user_creation import create_test_user
from property_street_backend.app.controllers.auth.services import fetched_access_token
from property_street_backend.app.schemas.auth_schemas import UserRegistrationSchema
from property_street_backend.app.controllers.chat.enums import MessageStatus, MessageTypes
from property_street_backend.app.controllers.chat.get_threads_schemas import (
    ThreadSummarySchema,
)
from property_street_backend.tests.activity.test_controller.test_objects import cloud_image_template


@pytest.mark.asyncio
async def test_get_threads_with_latest_message(client__fixture):
    test_db: AsyncSession = client__fixture['db']
    httpx_client: AsyncClient = client__fixture['http_client']

    # Create test users
    user1 = await create_test_user(test_db)
    user1.profile_avatar = CloudImageDetail(**cloud_image_template)
    test_db.add(user1)

    user2 = await create_test_user(test_db, UserRegistrationSchema(
        username='partner',
        email='partner@example.com',
        password='securepass',
        first_name="secure",
        last_name="pass"
    ))
    cloud_image_template["public_id"] = f"public_id_2"
    user2.profile_avatar = CloudImageDetail(**cloud_image_template)
    test_db.add(user2)

    token = fetched_access_token(user1)['access_token']
    headers = {"Authorization": f"Bearer {token}"}

    # Create multiple threads between them
    threads = []
    for i in range(3):
        messages = [
            Message(
                fmt_msg=FMTMSG.model_validate(fmt_msg).model_dump(),
                server_timestamp_ms=j,
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

    # commit all changes
    await test_db.commit()

    # Fetch threads for user1
    response = await httpx_client.get(
        '/chat/get-threads-meta',
        headers = headers,
    )
    results = response.json()


    # Verify structure and correctness
    assert len(results) == 3
    for thread_data in results:
        ThreadSummarySchema.model_validate(thread_data)
        assert thread_data['last_message']['sender']['profile_avatar']['url']