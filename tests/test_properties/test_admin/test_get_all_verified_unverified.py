import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import Asset
from app.controllers.auth.services import fetch_access_token
from property_street_backend.app.controllers.auth.utils import ensure_admin_user
from property_street_backend.tests.test_properties.test_processing import property_payload
from property_street_backend.app.controllers.assets.relationship_handler import apply_model
from property_street_backend.tests.auth.test_create_agent import create_test_agent, UserRegistrationSchema


@pytest.mark.asyncio
async def test_get_all_verified_unverified(client__fixture: dict):
    """Create 5 assets via apply_model, then POST the 6th to the endpoint and expect 400."""
    test_db: AsyncSession = client__fixture["db"]
    httpx_client: AsyncClient = client__fixture["http_client"]

    # create agent and mark as beta
    agent = await create_test_agent(test_db)
    admin = await ensure_admin_user(test_db)
    admin_token = fetch_access_token(user=admin)["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    amount = 5
    inst_lists = []
    # create five assets using apply_model directly
    for _ in range(amount):
        payload = property_payload(agent.id)
        inst = await apply_model(Asset, test_db, payload)
        assert inst is not None
        await asyncio.sleep(1) # To give a difference in time
        inst_lists.append(inst)
    
    verified_insts = []
    property_count_to_validate = 2
    for i in range(property_count_to_validate):
        inst = inst_lists[i]
        inst.verified = True
        verified_insts.append(inst)
    test_db.add_all(verified_insts)
    await test_db.commit()

    # Make all request
    response = await httpx_client.get("/admin/properties/all/",headers=admin_headers)
    assert response.status_code == 200
    json_resp = response.json()
    assert len(json_resp) == amount
    
    # Make unverified request
    response = await httpx_client.get("/admin/properties/unverified/",headers=admin_headers)
    assert response.status_code == 200
    assert len(response.json()) == amount - property_count_to_validate
    
    # Make verified request
    response = await httpx_client.get("/admin/properties/verified/",headers=admin_headers)
    assert response.status_code == 200
    assert len(response.json()) == property_count_to_validate    