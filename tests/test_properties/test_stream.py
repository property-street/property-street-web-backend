import pytest
from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import (
    User,
    Asset,
    Area,
    Tag,
    AssetCloudImage,
    CloudImageDetail,
)
from property_street_backend.app.controllers.auth.services import fetch_access_token
from property_street_backend.tests.auth.test_create_agent import create_test_agent
from property_street_backend.tests.activity.test_controller.test_objects import (
    area_template,
    cloud_image_template,
)
from property_street_backend.app.controllers.assets.model_utils import UserStatsPerProperty



def _make_test_assets(agent_id: int, size: int = 2):
    return [
        Asset(
            agent_id=agent_id,
            title=f"Test Asset {i}",
            currency="USD",
            price=5000.0,
            lease_duration="6 months",
            description="Test Description",
            category="Category Y",
            status="Available",
            verified=True,
            listing_type="sale",
            area=Area(**area_template),
            cover_image=CloudImageDetail(
                **{
                    **cloud_image_template,
                    "public_id": f"test_public_id{i}",
                }
            ),
            tags=[Tag(name=f"tag {i}{j}") for j in range(2)],
            unfeatured_images=[
                AssetCloudImage(
                    **{
                        **cloud_image_template,
                        "public_id": f"test_public_id{i}{j}",
                    }
                )
                for j in range(2)
            ],
        )
        for i in range(size)
    ]


@pytest.mark.asyncio
async def test_stream_returns_user_stats(client__fixture):
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]
    # Create a test agent (user)
    agent: User = await create_test_agent(test_db)

    # Create 2 assets
    assets = _make_test_assets(agent.id, size=2)
    test_db.add_all(assets)
    await test_db.commit()

    # Ensure assets have IDs
    for asset in assets:
        await test_db.refresh(asset)

    # Create a user stats record for the first asset
    stats = UserStatsPerProperty(
        asset_id=assets[0].id,
        user_id=agent.id,
        liked=True,
        saved=True,
        share_count=2,
        view_count=3,
    )
    test_db.add(stats)
    await test_db.commit()

    token = fetch_access_token(agent)["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = await httpx_client.post(
        "/assets/stream/", headers=headers,
        json={"seen_ids": [], "db_cursor": None, "auto_cat_cursor": None}
    )
    assert response.status_code == 200
    json_resp = response.json()
    assert isinstance(json_resp, dict)
    assets_resp = json_resp.get('data')
    assert assets_resp
    assert len(assets_resp) >= 1

    # Find the asset with known stats
    targeted = next((a for a in assets_resp if a["id"] == assets[0].id), None)
    assert targeted is not None
    assert targeted.get("user_stats") is not None
    assert targeted["user_stats"]["liked"] is True
    assert targeted["user_stats"]["save"] is True
    assert targeted["user_stats"]["share_count"] == 2
    assert targeted["user_stats"]["view_count"] == 3

    # Other assets should still include user_stats (defaults)
    other = next((a for a in assets_resp if a["id"] == assets[1].id), None)
    assert other is not None
    assert other.get("user_stats") is not None
    assert other["user_stats"]["liked"] is False


@pytest.mark.asyncio
async def test_stream_respects_seen_ids(client__fixture):
    httpx_client: AsyncClient = client__fixture["http_client"]
    test_db: AsyncSession = client__fixture["db"]
    # Create a test agent (user)
    agent: User = await create_test_agent(test_db)

    # Create 5 assets
    assets = _make_test_assets(agent.id, size=5)
    test_db.add_all(assets)
    await test_db.commit()

    # Ensure assets have IDs
    for asset in assets:
        await test_db.refresh(asset)

    token = fetch_access_token(agent)["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # First call without seen_ids
    response = await httpx_client.post("/assets/stream/", headers=headers)
    assert response.status_code == 200

    assets_resp = response.json()
    assert isinstance(assets_resp, list)
    assert len(assets_resp) == 5  # All assets returned

    # Get IDs of first 2 assets
    seen_ids = [assets_resp[0]["id"], assets_resp[1]["id"]]

    # Second call with seen_ids
    params = {"seen_ids": seen_ids}
    response = await httpx_client.post("/assets/stream/", headers=headers, params=params)
    assert response.status_code == 200

    assets_resp_2 = response.json()
    assert isinstance(assets_resp_2, list)
    assert len(assets_resp_2) == 3  # 5 - 2 = 3

    # Ensure seen_ids are not in the response
    returned_ids = [a["id"] for a in assets_resp_2]
    assert seen_ids[0] not in returned_ids
    assert seen_ids[1] not in returned_ids

    # Ensure the remaining assets are the ones not seen
    expected_ids = [a.id for a in assets[2:]]
    assert set(returned_ids) == set(expected_ids)
