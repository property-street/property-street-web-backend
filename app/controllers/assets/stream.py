from math import ceil
from sqlalchemy import or_
from datetime import datetime
from redis.asyncio import Redis
from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Asset, Tag
from .schemas import StreamPayload
from .search import area_ilike_tuple
from .utils import eager_asset_load
from .s_utils import (
    default_zset_subs,
    load_assets_by_ids,
    MAX_RESULTS_PER_STREAM,
    auto_cat_tracker_zset_key,
    AutoCategoryStreamLastScoreManager,

)
from property_street_backend.app.models import User
from property_street_backend.config.settings import logger, DEBUG
from property_street_backend.app.models_helper import Area
from .settings import USER_PREFERENCE_STREAM_ENTRY_CURSOR_EXPIRY

max_result_per_stream = MAX_RESULTS_PER_STREAM


async def load_stream_state(
    user: User | None,
    db: AsyncSession,
    redis_client: Redis,
    stream_payload: StreamPayload,
) -> dict:
    
    results: List[Asset] = []
    user_id = user.id if user else None

    # Convert to set for O(1) lookups
    seen_ids_set = set(stream_payload.seen_ids or [])

    db_cursor = stream_payload.db_cursor
    auto_category_next_score = stream_payload.auto_cat_cursor
    next_cursor = db_cursor

    # ----------------------------
    # 1. Preference-based stream
    # ----------------------------
    rows, next_cursor = await load_stream_state_from_preference(
        db,
        redis_client,
        list(seen_ids_set),
        user_id,
        db_cursor
    )
    if DEBUG:
        logger.info(f"**Preference rows: {rows}")
    results.extend(rows)

    # Extend seen ids immediately
    seen_ids_set.update(a.id for a in rows)

    # ----------------------------
    # 2. Auto-categories discovery
    # ----------------------------
    auto_category_next_score = "+inf"
    if len(results) < MAX_RESULTS_PER_STREAM:
        
        rows, auto_category_next_score = await load_stream_state_from_auto_categories(
            db,
            redis_client,
            limit=MAX_RESULTS_PER_STREAM - len(results),
            seen_ids=list(seen_ids_set),
            last_score=stream_payload.auto_cat_cursor,
            user_id=user_id
        )
        if DEBUG:
            logger.info(f"**Auto categories rows: {rows}")
        results.extend(rows)

        # Extend seen ids again
        seen_ids_set.update(a.id for a in rows)

    # ----------------------------
    # 3. DB hard fallback
    # ----------------------------
    if len(results) < MAX_RESULTS_PER_STREAM:

        rows, next_cursor = await load_stream_state_from_db(
            db,
            limit=MAX_RESULTS_PER_STREAM - len(results),
            cursor=db_cursor,
            seen_ids=list(seen_ids_set),
        )
        if DEBUG:
            logger.info(f"**Fallback rows: {rows}")
        results.extend(rows)

        # Extend seen ids again
        seen_ids_set.update(a.id for a in rows)

    return {
        "data": results,
        "seen_ids": list(seen_ids_set),
        "auto_cat_cursor": auto_category_next_score,
        "db_cursor": next_cursor,
    }


async def load_stream_state_from_preference(
    db: AsyncSession,
    redis_client: Redis,
    seen_ids: List[int],
    user_id: int | None = None,
    cursor: str | None = None,
) -> List[Asset]:
    # 1. Load preference zsets (ordered lists)
    result: Dict[str, List[str]] = {}

    if user_id:
        for field in default_zset_subs.keys():
            redis_key = f"preferences:{user_id}:{field}"
            values = await redis_client.zrange(redis_key, 0, -1)

            if values:
                # Redis may return bytes; normalize to str for SQL comparisons
                decoded = [v.decode() if isinstance(v, (bytes, bytearray)) else v for v in values]
                result[field] = decoded
    
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

        idx = await next_preference(redis_client, user_id or -1, field, len(keywords))
        keyword = keywords[idx]

        quotas.append({
            "field": field,
            "keyword": keyword,
            "limit": per_field_limit,
        })

    results = []

    next_cursor = None
    if quotas:
        n = len(quotas)
        for idx in range(n):
            quota = quotas[idx]
            rows, last_cursor = await query_assets_by_preference(
                db,
                quota["field"],
                quota["keyword"],
                limit=quota["limit"],
                cursor=cursor,
                seen_ids=seen_ids,
                strict=True,
            )
            results.extend(rows)
            if idx == (n-1):
                next_cursor = last_cursor 

    return results, next_cursor


async def load_stream_state_from_auto_categories(
    db: AsyncSession,
    redis_client: Redis,
    *,
    limit: int,
    seen_ids: list[int],
    last_score: float | None = None,
    user_id: int | None = None,
) -> tuple[List[int], float | None]:
    """
    Returns asset_ids + new cursor score
    """
    max_score = None
    if user_id:
        last_score_manager = AutoCategoryStreamLastScoreManager(user_id)
        max_score = (await last_score_manager.get_auto_cat_stream_last_score(redis_client)) or "+inf"
    else:
        # Default: start from top
        max_score = last_score or "+inf"

    rows = await redis_client.zrevrangebyscore(
        auto_cat_tracker_zset_key,
        max=max_score,
        min="-inf",
        start=0,
        num=limit * 2,  # overfetch for dedup
        withscores=True,
    )
 
    asset_ids = []
    next_score = None

    for asset_id, score in rows:
        asset_id = int(asset_id)

        if asset_id in seen_ids:
            continue

        asset_ids.append(asset_id)
        next_score = score

        if len(asset_ids) == limit:
            break

    # Persist next score
    if user_id:
        await last_score_manager.update_auto_cat_stream_last_score(next_score, redis_client)

    results = []
    if asset_ids:
        rows = await load_assets_by_ids(db, asset_ids)
        results.extend(rows)

    return results, next_score


async def load_stream_state_from_db(
    db: AsyncSession,
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
    return rows, next_cursor


async def next_preference(redis_client: Redis, user_id: int, field: str, size: int) -> int:
    user_preference_stream_entry_cursor = f"stream:preferences:index:{user_id}"
    idx = await redis_client.hincrby(
        user_preference_stream_entry_cursor,
        field,
        1
    )
    await redis_client.expire(user_preference_stream_entry_cursor, USER_PREFERENCE_STREAM_ENTRY_CURSOR_EXPIRY)
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

    elif field == "tags":
        stmt = stmt.join(Asset.tags)\
                .where(Tag.name.ilike(like_pattern))\
                .distinct()

    elif field == "location":
        stmt = stmt.join(Asset.area).where(
            *area_ilike_tuple(like_pattern)
        )

    elif field == "others":
        stmt = stmt.where(
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
