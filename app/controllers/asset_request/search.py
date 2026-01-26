from typing import List
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from .models import AssetRequest
from property_street_backend.app.models import Area
from .schemas import PropertyRequestSchema, PropertyRequestSearchResponse
from property_street_backend.config.postgres_connection_manager import runtime_async_session_maker

async def search_asset_requests(query_data: dict) -> List[PropertyRequestSearchResponse]:
    AsyncSessionLocal = runtime_async_session_maker()
    async with AsyncSessionLocal() as db:
        keywords = query_data['keywords']
        if not keywords:
            return []
        stmt = (
            select(AssetRequest)
            .join(Area)
            .where(or_(
                *[AssetRequest.description.ilike(f"%{kw}%") for kw in keywords],
                # Area
                *[Area.country.ilike(f"%{kw}%") for kw in keywords],
                *[Area.state_or_province.ilike(f"%{kw}%") for kw in keywords],
                *[Area.city_or_town.ilike(f"%{kw}%") for kw in keywords],
                *[Area.street.ilike(f"%{kw}%") for kw in keywords],
            ))
            .limit(20)
        )
        results = (await db.execute(stmt)).scalars().all()
        return [{"type": "property-request", "data": PropertyRequestSchema.from_orm_with_relations(r).model_dump()} for r in results]