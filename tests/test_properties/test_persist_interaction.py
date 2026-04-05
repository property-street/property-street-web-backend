import pytest
from httpx import AsyncClient
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import User, Asset
from property_street_backend.tests.test_properties import create_test_asset
from property_street_backend.app.controllers.assets.enums import InteractionType
from property_street_backend.tests.auth.test_create_agent import create_test_agent
from property_street_backend.app.controllers.auth.services import fetch_access_token
from property_street_backend.app.controllers.assets.models import PropertyInteractionEvent
from property_street_backend.app.controllers.assets.schemas import (
    InteractionEvents,
    PropertyInteractionSchema,
)
from property_street_backend.app.controllers.assets.model_utils import UserStatsPerProperty


def _interaction_payload(asset_id: int, start_ms: int) -> list[PropertyInteractionEvent]:
    """
    Build a full interaction payload (all InteractionType values) for one asset.

    NOTE:
    `InteractionData.action` is currently typed as Literal[0,1] in schema, while the
    service matches against `InteractionType`. We use `model_construct` to encode
    the functional shape expected by the service layer.
    """
    interaction_types = [
        InteractionType.like,
        InteractionType.save,
        InteractionType.cart,
        InteractionType.share,
        InteractionType.view,
        InteractionType.click,
        InteractionType.contact,
    ]

    return {
        asset_id: {
            type: [{
                "timestamp_ms": start_ms + (index * 10),
                "action": 1,
            }] for index, type in enumerate(interaction_types)
        } 
    }


@pytest.mark.asyncio
async def test_handle_persist_property_interaction_all_types_persisted(
    client__fixture,
):
    test_db: AsyncSession = client__fixture["db"]
    httpx_client: AsyncClient = client__fixture["http_client"]

    test_agent: User = await create_test_agent(test_db)
    test_asset: Asset = await create_test_asset(test_db, agent_id=test_agent.id)

    initial_asset = await test_db.get(Asset, test_asset.id)

    initial_events = (
        await test_db.execute(
            select(PropertyInteractionEvent).where(
                PropertyInteractionEvent.property_id == test_asset.id
            )
        )
    ).scalars().all()
    initial_events_count = len(initial_events)

    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    payload = _interaction_payload(test_asset.id, now_ms)
    PropertyInteractionSchema.model_validate(payload)
    
    token = fetch_access_token(user=test_agent)['access_token']
    headers = {"Authorization": f"Bearer {token}"}
    response = await httpx_client.post(
        '/assets/persist-interaction/',
        headers=headers,
        json=payload,
    )
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "success"
    assert result["count"] == 7

    refreshed_asset: Asset = await test_db.get(Asset, test_asset.id)

    assert refreshed_asset.likes == 1
    assert refreshed_asset.saves == 1
    assert refreshed_asset.carts == 1
    assert refreshed_asset.shares == 1
    assert refreshed_asset.views == 0
    assert refreshed_asset.clicks == 1
    assert refreshed_asset.contacts == 1

    stats = (
        await test_db.execute(
            select(UserStatsPerProperty).where(
                UserStatsPerProperty.asset_id == test_asset.id,
                UserStatsPerProperty.user_id == test_agent.id,
            )
        )
    ).scalars().first()

    assert stats is not None
    assert stats.liked is True
    assert stats.saved is True
    assert stats.cart is True
    assert stats.share_count == 1
    assert stats.view_count == 0
    assert stats.click_count == 1
    assert stats.contact_count == 1

    final_events = (
        await test_db.execute(
            select(PropertyInteractionEvent).where(
                PropertyInteractionEvent.property_id == test_asset.id
            )
        )
    ).scalars().all()

    assert len(final_events) == initial_events_count + 7

    # persisted_factors = [event.factor for event in final_events[-7:]]
    # assert persisted_factors == [
    #     InteractionType.like,
    #     InteractionType.save,
    #     InteractionType.cart,
    #     InteractionType.share,
    #     InteractionType.view,
    #     InteractionType.click,
    #     InteractionType.contact,
    # ]


@pytest.mark.asyncio
async def test_handle_persist_property_interaction_like_singleton_dedup(
    client__fixture,
):
    test_db: AsyncSession = client__fixture["db"]
    httpx_client: AsyncClient = client__fixture["http_client"]

    test_agent: User = await create_test_agent(test_db)
    test_asset: Asset = await create_test_asset(test_db, agent_id=test_agent.id)

    initial_asset = await test_db.get(Asset, test_asset.id)
    assert initial_asset.likes == 0

    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    payload = {
        test_asset.id: {
            InteractionType.like: [
                {"timestamp_ms": now_ms, "action": 1},
                {"timestamp_ms": now_ms + 1, "action": 1},
            ]
        }
    }

    PropertyInteractionSchema.model_validate(payload)

    token = fetch_access_token(user=test_agent)["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = await httpx_client.post(
        '/assets/persist-interaction/',
        headers=headers,
        json=payload,
    )

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "success"
    assert result["count"] == 1

    refreshed_asset: Asset = await test_db.get(Asset, test_asset.id)
    assert refreshed_asset.likes == 1

    stats = (
        await test_db.execute(
            select(UserStatsPerProperty).where(
                UserStatsPerProperty.asset_id == test_asset.id,
                UserStatsPerProperty.user_id == test_agent.id,
            )
        )
    ).scalars().first()

    assert stats is not None
    assert stats.liked is True

    final_events = (
        await test_db.execute(
            select(PropertyInteractionEvent).where(
                PropertyInteractionEvent.property_id == test_asset.id
            )
        )
    ).scalars().all()

    assert len(final_events) == 1
    assert final_events[0].factor == InteractionType.like


@pytest.mark.asyncio
async def test_fetch_latest_assets_includes_user_stats_and_engagement_fields(
    client__fixture,
):
    test_db: AsyncSession = client__fixture["db"]
    httpx_client: AsyncClient = client__fixture["http_client"]

    test_agent: User = await create_test_agent(test_db)
    test_asset: Asset = await create_test_asset(test_db, agent_id=test_agent.id)

    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    payload = {
        test_asset.id: {
            InteractionType.like: [{"timestamp_ms": now_ms, "action": 1}],
            InteractionType.view: [{"timestamp_ms": now_ms + 1, "action": 1}],
        }
    }

    token = fetch_access_token(user=test_agent)["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    response = await httpx_client.post(
        '/assets/persist-interaction/',
        headers=headers,
        json=payload,
    )
    assert response.status_code == 200

    latest_response = await httpx_client.get(
        '/assets/latests?page=1&size=10',
        headers=headers,
    )
    assert latest_response.status_code == 200
    items = latest_response.json()
    assert items, "Expected at least one asset"

    matched = next((a for a in items if a['id'] == test_asset.id), None)
    assert matched is not None

    assert matched['likes'] == 1
    assert matched['total_ratings'] == 0
    assert matched['total_stars'] == 0
    assert matched['user_stats']['liked'] is True
    assert matched['user_stats']['view_count'] == 1

