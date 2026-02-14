import json
from math import ceil
from sqlalchemy import or_
from datetime import datetime
from redis.asyncio import Redis
from typing import List, Dict, Any
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Asset, Tag
from .search import area_ilike_tuple
from .services import eager_asset_load
from .s_utils import (
    db_stream_cursor,
    default_zset_subs,
    load_assets_by_ids,
    MAX_RESULTS_PER_STREAM,
    db_fallback_stream_cursor,
    auto_cat_tracker_zset_key,
    auto_cat_stream_last_score,
    load_datetime_cursor_from_redis,
    persist_datetime_cursor_to_redis,

)
from property_street_backend.app.models_helper import Area

max_result_per_stream = MAX_RESULTS_PER_STREAM


async def load_stream_state_from_preference(
    user_id: int,
    db: AsyncSession,
    redis_client: Redis,
    seen_ids: List[int],
    cursor: str | None = None,
) -> List[Asset]:
    # 1. Load preference zsets (ordered lists)
    result: Dict[str, List[str]] = {}

    for field in default_zset_subs.keys():
        redis_key = f"preferences:{user_id}:{field}"
        values = await redis_client.zrange(redis_key, 0, -1)

        if values:
            result[field] = values

    # 2. Fallback to defaults
    if not result:
        result = {
            field: list(values)
            for field, values in default_zset_subs.items()
        }

    # 3. Fair quota allocation
    field_count = len(result)
    per_field_limit = ceil(MAX_RESULTS_PER_STREAM / field_count)

    quotas = []

    for field, keywords in result.items():
        if not keywords:
            continue

        idx = await next_preference(redis_client, user_id, field, len(keywords))
        keyword = keywords[idx]

        quotas.append({
            "field": field,
            "keyword": keyword,
            "limit": per_field_limit,
        })

    results = []

    for quota in quotas:
        rows = await query_assets_by_preference(
            db,
            quota["field"],
            quota["keyword"],
            limit=quota["limit"],
            cursor=cursor,
            seen_ids=seen_ids,
            strict=True,
        )
        results.extend(rows)

    return results


async def load_stream_state(
    user_id: int,
    db: AsyncSession,
    redis_client: Redis, 
    seen_ids: List[int],
):
    results = []

    cursor: datetime = await load_datetime_cursor_from_redis(db_stream_cursor, redis_client)
    
    # 1. Preference-based quotas
    rows = await load_stream_state_from_preference(
        user_id, db, redis_client, seen_ids, cursor
    )        
    results.extend(rows)

    # 2. Auto-categories (Redis discovery)
    if len(results) < MAX_RESULTS_PER_STREAM:
        last_score_cursor = await redis_client.get(auto_cat_stream_last_score)
        rows = await load_stream_state_from_auto_categories(
            redis_client,
            limit=MAX_RESULTS_PER_STREAM - len(results),
            last_score=last_score_cursor,
            seen_ids=seen_ids,
        )
        results.extend(rows)

    # 3. DB hard fallback
    if len(results) < MAX_RESULTS_PER_STREAM:
        rows = await load_stream_state_from_db(
            db, redis_client,
            limit=MAX_RESULTS_PER_STREAM - len(results),
            cursor=cursor,
            seen_ids=seen_ids,
        )
        results.extend(rows)


async def load_stream_state_from_auto_categories(
    db: AsyncSession,
    redis_client: Redis,
    *,
    limit: int,
    last_score: float | None,
    seen_ids: list[int],
) -> tuple[List[int], float | None]:
    """
    Returns asset_ids + new cursor score
    """

    # Default: start from top
    max_score = last_score if last_score is not None else "+inf"

    rows = await redis_client.zrevrangebyscore(
        auto_cat_tracker_zset_key,
        max=max_score,
        min="-inf",
        start=0,
        num=limit * 2,  # overfetch for dedup
        withscores=True,
    )
 
    asset_ids = []
    next_cursor = None

    for asset_id, score in rows:
        asset_id = int(asset_id)

        if asset_id in seen_ids:
            continue

        asset_ids.append(asset_id)
        next_cursor = score

        if len(asset_ids) == limit:
            break

    # Persist last score
    await redis_client.set(auto_cat_stream_last_score, next_cursor)

    results = []
    if asset_ids:
        rows = await load_assets_by_ids(db, asset_ids)
        results.extend(rows)

    return results


async def load_stream_state_from_db(
    db: AsyncSession,
    redis_client: Redis,
    *,
    limit: int,
    cursor: datetime | None,
    seen_ids: list[int],
):
    stmt = (
        eager_asset_load()
        .where(
            Asset.verified.is_(True),
            ~Asset.id.in_(seen_ids),
        )
        .order_by(Asset.created_at.desc())
        .limit(limit)
    )

    if cursor:
        stmt = stmt.where(Asset.created_at < cursor)

    rows = (await db.execute(stmt)).scalars().all()

    next_cursor = rows[-1].created_at if rows else cursor
    # cache the newer cursor
    await persist_datetime_cursor_to_redis(
        db_fallback_stream_cursor, next_cursor, redis_client
    )
    return rows


async def next_preference(redis_client: Redis, user_id: int, field: str, size: int) -> int:
    idx = await redis_client.hincrby(
        f"stream:preferences:index:{user_id}",
        field,
        1
    )
    return idx % size


async def query_assets_by_preference(
    db: AsyncSession,
    field: str,
    keyword: str,
    *,
    limit: int,
    cursor: datetime | None,
    seen_ids: list[int],
    **kwargs
):
    stmt = eager_asset_load().where(
        Asset.verified.is_(True),
        ~Asset.id.in_(seen_ids),
    )

    if cursor:
        stmt = stmt.where(Asset.created_at < cursor)

    like_pattern = f"%{keyword}%"
    if field == "categories":
        stmt = stmt.where(Asset.category.ilike(like_pattern))
    if field == "tags":
        stmt = stmt.where(Tag.name.ilike(like_pattern))
    elif field == "location":
        stmt = stmt.join(Area).where(
            *area_ilike_tuple(like_pattern)
        )
    elif field == "others":
        stmt = stmt.join(Area).where(
            or_(
                Asset.title.ilike(like_pattern),
                Asset.description.ilike(like_pattern),
                Asset.category.ilike(like_pattern),
                Asset.lease_duration.ilike(like_pattern),
                Asset.status.ilike(like_pattern),
                Asset.listing_type.ilike(like_pattern),
            )
        )

    stmt = stmt.order_by(Asset.created_at.desc()).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    next_cursor = rows[-1].created_at if rows else cursor

    return rows, next_cursor
