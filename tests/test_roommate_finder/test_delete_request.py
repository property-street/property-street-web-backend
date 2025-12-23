import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.controllers.auth.services import fetched_access_token
from property_street_backend.app.controllers.roommate_finder.models import RoommateFinder
from property_street_backend.app.models import Area, CloudImageDetail
from property_street_backend.tests.auth.test_user_creation import create_test_user


@pytest.mark.asyncio
async def test_owner_can_delete_request(client__fixture):
    test_db: AsyncSession = client__fixture['db']
    http_client: AsyncClient = client__fixture['http_client']

    user = await create_test_user(test_db)

    # create a roommate request
    area_payload = {
        'country': 'X',
        'state_or_province': 'Y',
        'city_or_town': 'Z',
        'street': '1 Main St',
    }
    img = {
        'cloud_asset_id': 'a', 'format': 'jpg', 'bytes': 10,
        'height': 100, 'public_id': 'p', 'secure_url': 'https://example.com/p.jpg','width':100
    }

    rf = RoommateFinder(
        area=Area(**area_payload),
        max_roomies=1,
        extra_conditions='x',
        category='flat',
        requester_id=user.id,
        room_images=[CloudImageDetail(**img)]
    )
    test_db.add(rf)
    await test_db.flush()
    await test_db.commit()

    token = fetched_access_token(user)['access_token']
    headers = {'Authorization': f'Bearer {token}'}

    resp = await http_client.delete(f'/roommate-finder/requests/{rf.id}/', headers=headers)
    assert resp.status_code == 204

    # verify removed from db
    found = await test_db.get(RoommateFinder, rf.id)
    assert found is None


@pytest.mark.asyncio
async def test_non_owner_cannot_delete_request(client__fixture):
    test_db: AsyncSession = client__fixture['db']
    http_client: AsyncClient = client__fixture['http_client']

    owner = await create_test_user(test_db)
    other = await create_test_user(test_db)

    area_payload = {
        'country': 'X',
        'state_or_province': 'Y',
        'city_or_town': 'Z',
        'street': '1 Main St',
    }
    img = {
        'cloud_asset_id': 'a', 'format': 'jpg', 'bytes': 10,
        'height': 100, 'public_id': 'p', 'secure_url': 'https://example.com/p.jpg','width':100
    }

    rf = RoommateFinder(
        area=Area(**area_payload),
        max_roomies=1,
        extra_conditions='x',
        category='flat',
        requester_id=owner.id,
        room_images=[CloudImageDetail(**img)]
    )
    test_db.add(rf)
    await test_db.flush()
    await test_db.commit()

    token = fetched_access_token(other)['access_token']
    headers = {'Authorization': f'Bearer {token}'}

    resp = await http_client.delete(f'/roommate-finder/requests/{rf.id}/', headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_staff_can_delete_request(client__fixture):
    test_db: AsyncSession = client__fixture['db']
    http_client: AsyncClient = client__fixture['http_client']

    owner = await create_test_user(test_db)
    staff = await create_test_user(test_db)

    # promote staff
    staff.user_role = 'staff'
    test_db.add(staff)
    await test_db.commit()

    area_payload = {
        'country': 'X',
        'state_or_province': 'Y',
        'city_or_town': 'Z',
        'street': '1 Main St',
    }
    img = {
        'cloud_asset_id': 'a', 'format': 'jpg', 'bytes': 10,
        'height': 100, 'public_id': 'p', 'secure_url': 'https://example.com/p.jpg','width':100
    }

    rf = RoommateFinder(
        area=Area(**area_payload),
        max_roomies=1,
        extra_conditions='x',
        category='flat',
        requester_id=owner.id,
        room_images=[CloudImageDetail(**img)]
    )
    test_db.add(rf)
    await test_db.flush()
    await test_db.commit()

    token = fetched_access_token(staff)['access_token']
    headers = {'Authorization': f'Bearer {token}'}

    resp = await http_client.delete(f'/roommate-finder/requests/{rf.id}/', headers=headers)
    assert resp.status_code == 204

    found = await test_db.get(RoommateFinder, rf.id)
    assert found is None
