import pytest
from httpx import AsyncClient
from sqlalchemy.future import select
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import (
    User,
    Asset, 
)
from property_street_backend.app.initiator import logger
from .test_fetch_recent_assets import pre_commit_test_asset_collection
from property_street_backend.app.controllers.auth.utils import ensure_admin_user
from property_street_backend.tests.auth.test_create_agent import create_test_agent
from property_street_backend.app.controllers.auth.services import fetch_access_token
from property_street_backend.config.postgres_connection_manager import get_postgres_instance


@pytest.mark.asyncio
async def test_unverified_properties(client__fixture):

    # Unpack the client and test database from the fixture
    httpx_client: AsyncClient = client__fixture['http_client'] 
    test_db: AsyncSession = client__fixture['db']

    # Create a test agent/user
    created_agent: User = await create_test_agent(test_db)
    # Generate an access token for authentication
    agent_token = fetch_access_token(created_agent)['access_token']
    agent_headers = {"Authorization": f"Bearer {agent_token}"}

    admin = await ensure_admin_user()
    assert admin
    # Generate an access token for authentication
    admin_token = fetch_access_token(user=admin)['access_token']
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Create 10 assets
    test_assets = pre_commit_test_asset_collection(created_agent.id)
    property_length = len(test_assets)
    test_db.add_all(test_assets)
    await test_db.commit()

    #----------------------------
    # make a forbidden request
    #----------------------------
    response = await httpx_client.get(
        '/assets/unverified-properties/',
        headers=agent_headers,
    )
    assert response.status_code == 403

    #----------------------------
    # make http request
    #----------------------------
    response = await httpx_client.get(
        '/assets/unverified-properties/',
        headers = admin_headers
    )
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == property_length
    
    #--------------------------------------------------------
    # modify two properties to be unfit for verification
    #--------------------------------------------------------
    last_id = response_data[-1]['id']
    last_prty = await test_db.get(Asset,last_id)
    last_prty.datetime_declined = datetime.now(timezone.utc)
    
    last_2_id = response_data[-2]['id']
    last_2_prty = await test_db.get(Asset,last_2_id)
    last_2_prty.verified = True
    
    test_db.add_all([last_prty, last_2_prty])
    await test_db.commit()

    response = await httpx_client.get(
        '/assets/unverified-properties/',
        headers = admin_headers
    )
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == (property_length-2)