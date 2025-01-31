import json, time
import redis.asyncio as redis
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import (
    Tag,
    Asset,
)
from property_street_backend.app.schemas.asset_schemas import LatestAssetsFetchResponseSchema
from property_street_backend.app.schemas.asset_schemas import (
    AssetSchema
)


async def process_search_entries(
    entries: list, 
    redis_client: redis.Redis, 
    db_session: AsyncSession,
    expiry_seconds: int,
):
    results = []
    for entry in entries:
        token, tag = entry.split(":")

        # Cache lookup
        cache_key = f"recent_{token}"
        cached_value = await redis_client.get(cache_key)

        if cached_value: # serialized list of objects
            # Cache hit
            results.extend(json.loads(cached_value))
            # Update trending ZSET
            await redis_client.zincrby("trending_searches", 1, token)
            # Extend TTL
            await redis_client.expire(cache_key, expiry_seconds)  # 1-hour TTL
        else:
            all_serialized = []
            query_results = []

            if tag == "category":
                query_results = await db_session.execute(
                    select(Asset).where(Asset.category.ilike(f"%{token}%"))
                )
                query_results = query_results.scalars().all()

            elif tag == "none":
                # query for assets whose title match token
                name_results = await db_session.execute(
                    select(Asset).where(Asset.title.ilike(f"%{token}%"))
                )
                name_results = name_results.scalars().all()

                # query for assets whose tags match token
                tag_results = await db_session.execute(
                    select(Asset)
                    .join(Asset.tags)
                    .where(Tag.name.ilike(f"%{token}%"))
                    .options(selectinload(Asset.tags))
                )
                tag_results = tag_results.scalars().all()

                # custom set functionality to avoid duplicate result
                query_results = list({asset.id: asset for asset in name_results + tag_results}.values())

            if query_results:
                # serialize all result 
                # add them to the cache
                # extend the results list
                all_serialized = [
                    AssetSchema.model_validate(asset).model_dump() for asset in query_results
                ]
                await redis_client.set(cache_key, json.dumps(all_serialized), ex=expiry_seconds)
                results.extend(all_serialized)

            # add the search to the recent_searches zset
            await redis_client.zadd("recent_searches", {token: time.time()})

    return results
