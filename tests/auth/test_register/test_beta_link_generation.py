import pytest
import asyncio
from httpx import AsyncClient
from redis.asyncio import Redis
from urllib.parse import urlparse
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import create_test_user
from .. import UserRegistrationSchema
from property_street_backend.app.models import User
from property_street_backend.app.controllers.auth.utils import ensure_admin_user
from property_street_backend.app.controllers.auth.services import (
    beta_link_validity,
    fetch_access_token,
    hset_beta_signup_key,
)


@pytest.mark.asyncio
async def test_register_with_beta_token_validation(client__fixture):
    """Test registration flow with beta token validation when beta is enabled."""
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]
    redis_client: Redis = client__fixture["redis_client"]

    admin = await ensure_admin_user(test_db)
    assert admin
    admin_token = fetch_access_token(user=admin)['access_token']
    headers = {"Authorization": f"Bearer {admin_token}"}

    response = await httpx_client.get(
        '/auth/generate-beta-signup-link',
        headers = headers
    )
    assert response.status_code == 201
    data: dict = response.json()
    url = data.get("url")
    assert url
    parsed = urlparse(url)
    token = parsed.path.split("/")[-1]
    token = hset_beta_signup_key(token)
    assert await redis_client.exists(token)
    validity_ttl = beta_link_validity()

    await asyncio.sleep(validity_ttl+1)

    assert not await redis_client.exists(token)