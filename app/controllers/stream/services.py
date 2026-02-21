from redis.asyncio import Redis
from dataclasses import dataclass
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional

from property_street_backend.app.controllers.assets.services import category_candidates_stmt

@dataclass
class StreamState:
    seen_ids: set[int]
    category_weights: Dict[str, float]
    category_cursors: Dict[str, Optional[str]]


async def fetch_candidates(
    db: AsyncSession,
    state: StreamState,
    quotas: Dict[str, int],
):
    candidates = []

    for category, limit in quotas.items():
        cursor = state.category_cursors.get(category)

        stmt = category_candidates_stmt(
            category=category,
            cursor=cursor,
            seen_ids=list(state.seen_ids),
            limit=limit,
        )

        rows = (await db.execute(stmt)).scalars().all()
        candidates.extend(rows)

    return candidates


def score_asset(asset, state: StreamState) -> float:
    score = 0.0

    # Category preference
    score += state.category_weights.get(asset.category, 0.1)

    # Recency boost (simple decay)
    age_hours = (datetime.now(timezone.utc) - asset.created_at).total_seconds() / 3600
    score += max(0, 1 - age_hours / 72)

    # Popularity (optional field)
    score += getattr(asset, "popularity_score", 0) * 0.2

    return score


def rank_and_select(candidates, state: StreamState, limit=20):
    # [(score, asset), ...]
    scored = [(score_asset(a, state), a) for a in candidates]
    # Sorts the array of tuple from weightier to lighter in terms of scores
    scored.sort(key=lambda x: x[0], reverse=True)
    # Returns just the assets in the range of limit
    return [a for _, a in scored[:limit]]


async def update_state(redis: Redis, user_id: int, assets):
    seen_key = f"stream:{user_id}:seen"

    for asset in assets:
        await redis.sadd(seen_key, asset.id)

    await redis.expire(seen_key, 60 * 60 * 24 * 14)


def advance_cursors(state, assets):
    for asset in assets:
        state.category_cursors[asset.category] = asset.created_at


async def record_interaction(redis: Redis, user_id: int, asset, weight=0.3):
    key = f"stream:{user_id}:weights"
    await redis.hincrbyfloat(key, asset.category, weight)


DEFAULT_CATEGORY_WEIGHT = 0.1
STREAM_TTL_SECONDS = 60 * 60 * 24 * 14  # 14 days


async def load_stream_state(redis: Redis, user_id: int) -> StreamState:
    """
    Loads stream state from Redis.
    Handles cold start gracefully.
    """
    

    seen_key = f"stream:{user_id}:seen"
    weights_key = f"stream:{user_id}:weights"
    cursor_prefix = f"stream:{user_id}:cursor:"

    # -----------------------------
    # Load seen asset IDs
    # -----------------------------
    seen_ids_raw = await redis.smembers(seen_key)
    seen_ids = {int(x) for x in seen_ids_raw} if seen_ids_raw else set()

    # -----------------------------
    # Load category weights
    # -----------------------------
    raw_weights = await redis.hgetall(weights_key)

    category_weights = (
        {k.decode(): float(v) for k, v in raw_weights.items()}
        if raw_weights
        else {}
    )

    # -----------------------------
    # Load cursors (dynamic keys)
    # -----------------------------
    category_cursors: dict[str, Optional[str]] = {}

    async for key in redis.scan_iter(match=f"{cursor_prefix}*"):
        category = key.decode().replace(cursor_prefix, "")
        cursor_val = await redis.get(key)
        category_cursors[category] = (
            cursor_val.decode() if cursor_val else None
        )

    # -----------------------------
    # Cold start defaults
    # -----------------------------
    if not category_weights:
        category_weights = defaultdict(lambda: DEFAULT_CATEGORY_WEIGHT)

    # -----------------------------
    # Ensure TTLs exist (self-healing)
    # -----------------------------
    await redis.expire(seen_key, STREAM_TTL_SECONDS)
    await redis.expire(weights_key, STREAM_TTL_SECONDS)

    for category in category_cursors:
        await redis.expire(
            f"{cursor_prefix}{category}",
            STREAM_TTL_SECONDS,
        )

    return StreamState(
        seen_ids=seen_ids,
        category_weights=dict(category_weights),
        category_cursors=category_cursors,
    )