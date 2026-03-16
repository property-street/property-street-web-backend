import pytest
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone

from property_street_backend.app.models import (
    Asset,
    Area,
    Tag,
    CloudImageDetail,
)
from property_street_backend.app.controllers.assets.stream import (
    load_stream_state_from_preference,
    load_stream_state_from_auto_categories,
    load_stream_state_from_db,
)
from property_street_backend.app.controllers.assets.s_utils import auto_cat_tracker_zset_key
from property_street_backend.tests.auth.test_create_agent import create_test_agent
from property_street_backend.tests.activity.test_controller.test_objects import (
    area_template,
    cloud_image_template,
)


@pytest.mark.asyncio
async def test_load_stream_state_from_preference_uses_user_defined_preference(
    sessions_fixture,
):
    """When the user has preferences set, the stream should return assets matching those preferences."""
    db: AsyncSession = sessions_fixture["db"]
    redis_client: Redis = sessions_fixture["redis_client"]

    # Create a test agent (required for Asset.agent_id)
    agent = await create_test_agent(db)

    # Create a single asset that matches the preference keyword (category)
    asset = Asset(
        agent_id=agent.id,
        title="Stream Test Asset",
        currency="USD",
        price=10000,
        lease_duration="6 months",
        description="Test Description",
        category="studio apartment",  # matches default preferences
        status="Available",
        listing_type="Rent",
        area=Area(**area_template),
        cover_image=CloudImageDetail(**{**cloud_image_template, "public_id": "stream-asset"}),
        tags=[Tag(name="furnished")],
        verified=True,
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)

    # Set a user preference for categories to ensure deterministic behavior
    user_id = 1
    await redis_client.zadd(f"preferences:{user_id}:categories", {"studio apartment": 1})

    rows, next_cursor = await load_stream_state_from_preference(
        db=db,
        redis_client=redis_client,
        seen_ids=[],
        user_id=user_id,
        cursor=None,
    )

    assert rows, "Expected at least one asset returned from preference stream"
    assert any(r.id == asset.id for r in rows), "Expected the created asset to appear in preference results"
    assert next_cursor is not None


@pytest.mark.asyncio
async def test_load_stream_state_from_auto_categories_uses_redis_zset_and_updates_cursor(
    sessions_fixture,
):
    db: AsyncSession = sessions_fixture["db"]
    redis_client: Redis = sessions_fixture["redis_client"]

    agent = await create_test_agent(db)

    # Create two assets
    asset1 = Asset(
        agent_id=agent.id,
        title="Auto Category Asset 1",
        currency="USD",
        price=1000,
        lease_duration="3 months",
        description="Auto cat asset 1",
        category="Test",
        status="Available",
        listing_type="Rent",
        area=Area(**area_template),
        cover_image=CloudImageDetail(**{**cloud_image_template, "public_id": "auto1"}),
        verified=True,
    )
    asset2 = Asset(
        agent_id=agent.id,
        title="Auto Category Asset 2",
        currency="USD",
        price=2000,
        lease_duration="3 months",
        description="Auto cat asset 2",
        category="Test",
        status="Available",
        listing_type="Rent",
        area=Area(**area_template),
        cover_image=CloudImageDetail(**{**cloud_image_template, "public_id": "auto2"}),
        verified=True,
    )
    db.add_all([asset1, asset2])
    await db.commit()
    await db.refresh(asset1)
    await db.refresh(asset2)

    # Add their IDs to redis sorted set with scores
    await redis_client.zadd(auto_cat_tracker_zset_key, {str(asset1.id): 10, str(asset2.id): 20})

    # No user: should return highest score first
    rows, next_score = await load_stream_state_from_auto_categories(
        db=db,
        redis_client=redis_client,
        limit=1,
        seen_ids=[],
        last_score=None,
        user_id=None,
    )

    assert len(rows) == 1
    assert rows[0].id == asset2.id, "Expected highest-score asset returned first"
    assert next_score == 20

    # When user_id is provided, cursor should be persisted
    user_id = 123
    rows2, next_score2 = await load_stream_state_from_auto_categories(
        db=db,
        redis_client=redis_client,
        limit=1,
        seen_ids=[],
        last_score=None,
        user_id=user_id,
    )
    assert len(rows2) == 1
    assert await redis_client.get(f"auto:cat:stream:cursor:{user_id}") is not None


@pytest.mark.asyncio
async def test_load_stream_state_from_db_respects_seen_ids_and_ordering(
    sessions_fixture,
):
    db = sessions_fixture["db"]

    agent = await create_test_agent(db)

    now = datetime.now(timezone.utc)
    asset_earliest = Asset(
        agent_id=agent.id,
        title="DB Asset Earliest",
        currency="USD",
        price=100,
        lease_duration="1 month",
        description="Earliest",
        category="Test",
        status="Available",
        listing_type="Rent",
        area=Area(**area_template),
        cover_image=CloudImageDetail(**{**cloud_image_template, "public_id": "db-earliest"}),
        verified=True,
        created_at=now - timedelta(days=2),
    )
    asset_middle = Asset(
        agent_id=agent.id,
        title="DB Asset Middle",
        currency="USD",
        price=200,
        lease_duration="1 month",
        description="Middle",
        category="Test",
        status="Available",
        listing_type="Rent",
        area=Area(**area_template),
        cover_image=CloudImageDetail(**{**cloud_image_template, "public_id": "db-middle"}),
        verified=True,
        created_at=now - timedelta(days=1),
    )
    asset_latest = Asset(
        agent_id=agent.id,
        title="DB Asset Latest",
        currency="USD",
        price=300,
        lease_duration="1 month",
        description="Latest",
        category="Test",
        status="Available",
        listing_type="Rent",
        area=Area(**area_template),
        cover_image=CloudImageDetail(**{**cloud_image_template, "public_id": "db-latest"}),
        verified=True,
        created_at=now,
    )

    db.add_all([asset_earliest, asset_middle, asset_latest])
    await db.commit()
    await db.refresh(asset_earliest)
    await db.refresh(asset_middle)
    await db.refresh(asset_latest)

    rows, cursor = await load_stream_state_from_db(
        db=db,
        limit=2,
        cursor=None,
        seen_ids=[],
    )

    # Should return latest two assets by created_at desc
    assert [r.id for r in rows] == [asset_latest.id, asset_middle.id]
    assert cursor == asset_middle.created_at

    # When excluding the latest asset via seen_ids, get next two
    rows2, cursor2 = await load_stream_state_from_db(
        db=db,
        limit=2,
        cursor=None,
        seen_ids=[asset_latest.id],
    )
    assert [r.id for r in rows2] == [asset_middle.id, asset_earliest.id]
    assert cursor2 == asset_earliest.created_at
