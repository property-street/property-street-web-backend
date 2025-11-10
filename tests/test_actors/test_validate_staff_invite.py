import pytest

from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import User
from property_street_backend.tests.auth.test_user_creation import create_test_user
from property_street_backend.app.controllers.auth.schemas import UserRegistrationSchema
from property_street_backend.app.controllers.actors.services import staff_invite_hset_key


@pytest.mark.asyncio
async def test_validate_staff_invite_endpoint(client__fixture):
    """Test the /actors/validate-staff-invite/<token>/ endpoint in isolation.

    This test simulates the invite token being present in Redis under the
    `{user_id}:staff-invite` hset with field `token` and then calls the
    validate endpoint to ensure the user is upgraded and the cache removed.
    """
    # obtain fixtures
    httpx_client: AsyncClient = client__fixture['http_client']
    test_db: AsyncSession = client__fixture['db']
    redis_client: Redis = client__fixture['redis_client']

    # create a regular user to be invited
    created_user: User = await create_test_user(test_db)

    # simulate storing the invite token in redis
    token = f"invite_fixed_{created_user.id}"
    cache_key = staff_invite_hset_key(created_user.id)
    await redis_client.hset(cache_key, 'token', token)

    # call the validate endpoint
    resp = await httpx_client.post(f"/actors/validate-staff-invite/{token}/")
    assert resp.status_code == 200

    # check that the user was upgraded to staff
    updated_user: User = await test_db.get(User, created_user.id)
    assert updated_user.user_role == 'staff'

    # ensure redis key was cleaned up
    exists = await redis_client.exists(cache_key)
    assert exists == 0

    # also test mismatched token yields 400
    created_user2: User = await create_test_user(test_db,UserRegistrationSchema(
        email="crankgig@gmail.com",
        username="crankgig",
        password="password123",
        first_name="John",
        last_name="Doe",
    ))
    wrong_token = f"wrongtoken_{created_user2.id}"
    # store a different token so validation will fail
    await redis_client.hset(staff_invite_hset_key(created_user2.id), 'token', f"other_{created_user2.id}")
    resp2 = await httpx_client.post(f"/actors/validate-staff-invite/{wrong_token}/")
    assert resp2.status_code == 400
