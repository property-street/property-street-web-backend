from datetime import datetime
from redis.asyncio import Redis
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Asset

default_zset_subs = {
    # ----------------------------
    # Property category intent
    # ----------------------------
    "categories": [
        "self contain",
        "mini flat",
        "1 bedroom flat",
        "2 bedroom flat",
        "3 bedroom flat",
        "studio apartment",
        "serviced apartment",
        "duplex",
        "bungalow",
    ],

    # ----------------------------
    # Semantic tags / amenities
    # ----------------------------
    "tags": [
        "furnished",
        "semi-furnished",
        "serviced",
        "newly built",
        "secured estate",
        "gated compound",
        "parking",
        "24/7 power",
        "water supply",
        "pet friendly",
    ],

    # ----------------------------
    # Location signals (normalized)
    # ----------------------------
    "location": [
        "port harcourt",
        "lagos",
        "abuja",
        "ikeja",
        "lekki",
        "yaba",
        "gwarinpa",
        "trans amadi",
    ],

    # ----------------------------
    # Price bands (ZSET scores)
    # ----------------------------
    "price": [
        "below_300k",
        "300k_500k",
        "500k_800k",
        "800k_1.2m",
        "1.2m_plus",
    ],

    # ----------------------------
    # Listing attributes / meta
    # ----------------------------
    "others": [
        "featured",
        "recent",
        "popular",
        "discounted",
        "high_demand",
    ],
}

MAX_RESULTS_PER_STREAM = 15

auto_cat_tracker_zset_key = "auto:categories:tracker"
db_fallback_stream_cursor = "db:stream:cursor"
db_stream_cursor = "db:stream:cursor"
auto_cat_stream_last_score = "auto:cat:stream:cursor"

async def load_datetime_cursor_from_redis(key: str, redis_client: Redis) -> datetime|None:
    datetime_str = await redis_client.get(key)
    if not datetime_str:
        return None
    cursor = None

    try:
        cursor = datetime.fromisoformat(datetime_str)
    except: 
        pass

    return cursor

async def persist_datetime_cursor_to_redis(key: str, value: datetime, redis_client: Redis) -> datetime|None:
    await redis_client.set(key, value.isoformat())


async def load_assets_by_ids(db: AsyncSession, ids: list[int]):
    if not ids:
        return []

    stmt = select(Asset).where(Asset.id.in_(ids))
    rows = (await db.execute(stmt)).scalars().all()

    # Preserve Redis order
    asset_map = {a.id: a for a in rows}
    return [asset_map[i] for i in ids if i in asset_map]
