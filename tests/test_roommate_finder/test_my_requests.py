import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import Area, CloudImageDetail
from property_street_backend.app.controllers.auth.services import fetch_access_token
from property_street_backend.tests.auth import create_test_user, UserRegistrationSchema
from property_street_backend.app.controllers.roommate_finder.models import RoommateFinder


@pytest.mark.asyncio
async def test_my_requests_returns_only_user_requests(client__fixture):
    test_db: AsyncSession = client__fixture['db']
    http_client: AsyncClient = client__fixture['http_client']

    # Create two users
    user1 = await create_test_user(test_db)
    user2 = await create_test_user(test_db,UserRegistrationSchema(
        email="user2@example.com",
        username="user2",
        password="password123",
        first_name="John",
        last_name="Doe",
    ))

    # common payload pieces
    area_payload = {
        'country': 'CountryX',
        'state_or_province': 'StateY',
        'city_or_town': 'CityZ',
        'street': '12 Example St',
    }

    cloud_image_detail = {
        'cloud_asset_id': 'abc123',
        'format': 'jpg',
        'bytes': 1000,
        'height': 400,
        'public_id': 'img1',
        'secure_url': 'https://example.com/img1.jpg',
        'width': 600,
    }

    # Create 3 requests for user1 and 1 for user2
    requests = []
    for i in range(3):
        rf = RoommateFinder(
            area=Area(**area_payload),
            max_roomies=2,
            extra_conditions=f'cond {i}',
            category='flat',
            requester_id=user1.id,
            room_images=[CloudImageDetail(**{**cloud_image_detail, 'public_id': f'img_{i}'})]
        )
        requests.append(rf)

    # one for user2
    rf2 = RoommateFinder(
        area=Area(**area_payload),
        max_roomies=1,
        extra_conditions='other',
        category='hostel',
        requester_id=user2.id,
        room_images=[CloudImageDetail(**{**cloud_image_detail, 'public_id': 'img_other'})]
    )
    requests.append(rf2)

    test_db.add_all(requests)
    await test_db.flush()
    await test_db.commit()

    # Call endpoint as user1
    token = fetch_access_token(user1)['access_token']
    headers = {'Authorization': f'Bearer {token}'}

    resp = await http_client.get('/roommate-finder/my-requests', headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    # Should return only the 3 requests created by user1
    assert isinstance(data, list)
    assert len(data) == 3
    # Ensure none of the returned requests belong to user2
    returned_requester_ids = {(item.get('requester'))['id'] for item in data}
    assert all(rid == user1.id for rid in returned_requester_ids)
