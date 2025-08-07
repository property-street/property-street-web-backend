import pytest
from httpx import AsyncClient
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession


from property_street_backend.app.models import User
from property_street_backend.app.controllers.auth.services import (
    fetch_access_token,
)
from property_street_backend.tests.auth.test_create_agent import create_test_agent


@pytest.mark.asyncio
async def test_user_deletion(client__fixture):
    # get the yield client objects
    async for fixture_obj in client__fixture:
        # extract the database entry
        test_db: AsyncSession = fixture_obj["db"]
        httpx_client: AsyncClient = fixture_obj["http_client"]
        break
    
    created_user: User = await create_test_agent(test_db)
    tokenObj = fetch_access_token(user=created_user)

    # Generate an access token for authentication
    token = tokenObj['access_token']
    headers = {"Authorization": f"Bearer {token}"}

    response = await httpx_client.post('/settings/delete-account',headers=headers)
    assert response.status_code == 200
    query = await test_db.execute(
        select(User)
        .where(User.id == created_user.id)
    )
    assert not query.scalars().first()