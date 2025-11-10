import pytest
from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import User
from property_street_backend.app.controllers.auth.utils import ensure_admin_user
from property_street_backend.tests.auth.test_user_creation import create_test_user
from property_street_backend.app.controllers.auth.services import fetch_access_token
from property_street_backend.app.controllers.auth.schemas import UserRegistrationSchema
from property_street_backend.app.controllers.actors.services import staff_invite_hset_key


@pytest.mark.asyncio
async def test_generate_and_validate_staff_invite(client__fixture):
    # fetch fixtures
    httpx_client: AsyncClient = client__fixture['http_client']
    test_db: AsyncSession = client__fixture['db']
    redis_client: Redis = client__fixture['redis_client']

    # create a normal test user (the invite target)
    created_user: User = await create_test_user(test_db, UserRegistrationSchema(
        email="crankgig@gmail.com",
        username="testuser",
        password="password123",
        first_name="John",
        last_name="Doe",
    ))
    user_id=created_user.id
    
    # ensure admin exists and get token
    admin = await ensure_admin_user()
    token_obj = fetch_access_token(user=admin)
    admin_token = token_obj['access_token']
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # generate invite link (admin-only endpoint)
    response = await httpx_client.post(
        f"/actors/generate-staff-invite-link/{user_id}/",
        headers=admin_headers,
    )
    assert response.status_code == 201

    # read the token from redis
    cache_key = staff_invite_hset_key(user_id)
    stored_token = await redis_client.hget(cache_key, 'token')
    assert stored_token is not None
    if isinstance(stored_token, bytes):
        stored_token = stored_token.decode()

    # validate the invite (no auth required)
    validate_resp = await httpx_client.post(f"/actors/validate-staff-invite/{stored_token}/")
    assert validate_resp.status_code == 200

    # verify the user role was upgraded in the database
    updated_user: User = await test_db.get(User, created_user.id)
    assert updated_user.user_role == 'staff'

    # ensure redis cleanup
    exists = await redis_client.exists(cache_key)
    assert exists == 0

