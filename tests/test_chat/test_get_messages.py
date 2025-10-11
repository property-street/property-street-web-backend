import pytest
import random
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient

from property_street_backend.app.models import Message, Thread
from property_street_backend.tests.auth.test_user_creation import create_test_user
from property_street_backend.app.schemas.auth_schemas import UserRegistrationSchema
from property_street_backend.app.controllers.auth.services import fetch_access_token

@pytest.mark.asyncio
async def test_get_messages( client__fixture ):
    test_db: AsyncSession = client__fixture['db']
    httpx_client: AsyncClient = client__fixture['http_client']

    sender = await create_test_user(test_db)
    recipient = await create_test_user(test_db, UserRegistrationSchema(
        username='recipient',
        email='recipient@example.com',
        password='strongpassword',
        first_name = 'joke',
        last_name = 'oed'
    ))

    token = fetch_access_token(sender)['access_token']
    headers = {"Authorization": f"Bearer {token}"}

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
    response1 = await httpx_client.get(
        f'/chat/get-messages/{recipient.id}',
        headers = headers,
        params = {
            'size': page1_size,
            'page': page1
        }
    )
    page1_response = response1.json()
    assert page1_response[0]['text_content'] == messages[-1].text_content
    assert page1_response[-1]['timestamp'] == messages[100-page1_size].timestamp

    # get second page of messages
    page2 = 2
    page2_size = 50
    response2 = await httpx_client.get(
        f'/chat/get-messages/{recipient.id}',
        headers = headers,
        params = {
            'size': page2_size,
            'page': page2
        }
    )
    page2_messages = response2.json()
    assert page2_messages[0]['text_content'] == messages[((page2-1) * page2_size)-1].text_content
    assert page2_messages[-1]['timestamp'] == messages[0].timestamp