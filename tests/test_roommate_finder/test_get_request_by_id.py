import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.tests.auth import create_test_user
from property_street_backend.app.controllers.auth.services import fetch_access_token
from property_street_backend.app.controllers.roommate_finder.schemas import RoommateFinderResponseSchema


@pytest.mark.asyncio
async def test_get_roommate_request_by_id(client__fixture):
    test_db: AsyncSession = client__fixture['db']
    http_client: AsyncClient = client__fixture['http_client']

    # create a test user
    user = await create_test_user(test_db)
    token_data = fetch_access_token(user)
    headers = {'Authorization': f"Bearer {token_data['access_token']}", 'Content-Type': 'application/json'}

    # payload similar to other tests
    payload = {
        'area': {
            'country':'Sri-lanka',
            'state_or_province': 'Mogadishu',
            'city_or_town': 'Pisque Central', 
            'street': 'No 11 Jokey street',
        },
        'max_roomies': 4,
        'room_images': [],
        'extra_conditions': 'I need a 1 bedroom flat in the maldives!',
        'gender': 'male',
        'category': 'hotel',
    }

    # create roommate request via endpoint
    resp = await http_client.post('/roommate-finder', json=payload, headers=headers)
    assert resp.status_code == 201
    created = resp.json()
    assert 'id' in created
    request_id = created['id']

    # fetch by id
    get_resp = await http_client.get(f'/roommate-finder/requests/{request_id}', headers=headers)
    assert get_resp.status_code == 200
    data = get_resp.json()
    RoommateFinderResponseSchema.model_validate(data)
    assert data['extra_conditions'] == payload['extra_conditions']
    assert data['max_roomies'] == payload['max_roomies']
    assert data['category'] == payload['category']
