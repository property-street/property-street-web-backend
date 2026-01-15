import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import Asset
from app.controllers.auth.services import fetch_access_token
from property_street_backend.config.settings import TEST_UNLIMITED_BETA_AGENTS_EMAIL
from property_street_backend.tests.test_properties.test_processing import property_payload
from property_street_backend.app.controllers.assets.relationship_handler import apply_model
from property_street_backend.tests.auth.test_create_agent import create_test_agent, UserRegistrationSchema


@pytest.mark.asyncio
async def test_beta_limit_endpoint(client__fixture: dict):
    """Create 5 assets via apply_model, then POST the 6th to the endpoint and expect 400."""
    test_db: AsyncSession = client__fixture["db"]
    http_client: AsyncClient = client__fixture["http_client"]

    # create agent and mark as beta
    agent = await create_test_agent(test_db)
    token = fetch_access_token(user=agent)["access_token"]
    headers = {"Authorization": f"Bearer {token}"}


    # create five assets using apply_model directly
    for _ in range(5):
        payload = property_payload(agent.id)
        inst = await apply_model(Asset, test_db, payload)
        assert inst is not None
        await asyncio.sleep(1)
    


    #==============================================================
    # Sixth creation via endpoint should be rejected (Bad Request)
    #==============================================================
    payload6 = property_payload(agent.id)
    response = await http_client.post(
        "/assets/create-property",
        json=payload6,
        headers=headers,
    )
    assert response.status_code == 400

    #========================================
    # But accepted for a prioritized user
    #========================================
    u_agent_data = UserRegistrationSchema(
        username='team',
        email=TEST_UNLIMITED_BETA_AGENTS_EMAIL,
        password='strongpassword',
        first_name = 'team'
    )
    u_beta_agent = await create_test_agent(test_db, u_agent_data)
    assert u_beta_agent.username == u_agent_data.username
    u_beta_agent_token = fetch_access_token(user=u_beta_agent)["access_token"]
    u_beta_agent_headers = {"Authorization": f"Bearer {u_beta_agent_token}"}
    payload6 = property_payload(u_beta_agent.id)
    response = await http_client.post(
        "/assets/create-property",
        json=payload6,
        headers=u_beta_agent_headers,
    )
    assert response.status_code == 201
