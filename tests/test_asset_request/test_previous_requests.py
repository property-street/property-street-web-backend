import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


from property_street_backend.app.initiator import logger
from property_street_backend.app.controllers.auth.services import fetch_access_token
from property_street_backend.tests.auth import create_test_user, UserRegistrationSchema
from property_street_backend.app.models import User, CloudImageDetail, AssetRequest, Area
from property_street_backend.tests.activity.test_controller.test_objects import area_template


@pytest.mark.asyncio
async def test_latest_collection(client__fixture):
    test_db: AsyncSession = client__fixture['db'] 
    httpx_client: AsyncClient = client__fixture['http_client']

    test_user: User = await create_test_user(test_db)
    test_user2 = await create_test_user(test_db, UserRegistrationSchema(
        email="testuser2@example.com",
        username="testuser2",
        password="password123",
        first_name="John",
        last_name="Doe",
    ))
    test_db.add(test_user2)
    await test_db.flush() # flush to reflect change

    saved_requests = 10
    # construct payload
    asset_requests = [
        AssetRequest(
            description = f'I need a 1 bedroom flat in the maldives! {i}',
            area = Area(**{
                **area_template,
                'zip_or_postal_code': "11bced",
                'building_name_or_suite': 'Quando-rondo'
            }),
            requester_id = test_user.id if (i%2 == 0) else test_user2.id,
        ) for i in range(saved_requests)
    ] 
    test_db.add_all(asset_requests)
    await test_db.flush()

    token = fetch_access_token(user=test_user)['access_token']
    headers = {"Authorization": f"Bearer {token}"}
    response = await httpx_client.get(f"/asset-requests/my-requests",headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == (saved_requests//2)