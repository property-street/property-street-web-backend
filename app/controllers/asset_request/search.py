from typing import List
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from .models import AssetRequest
from property_street_backend.app.models import Area
from .schemas import PropertyRequestSchema, PropertyRequestSearchResponse
from property_street_backend.config.postgres_connection_manager import runtime_async_session_maker

async def search_asset_requests(query_data: dict, limit: int = 20, seen_ids: List[int] = None) -> List[PropertyRequestSearchResponse]:
    if seen_ids is None:
        seen_ids = []
        
    AsyncSessionLocal = runtime_async_session_maker()
    async with AsyncSessionLocal() as db:
        keywords = query_data['keywords']
        if not keywords:
            return []
        
        where_conditions = or_(
            *[AssetRequest.description.ilike(f"%{kw}%") for kw in keywords],
            # Area
            *[Area.country.ilike(f"%{kw}%") for kw in keywords],
            *[Area.state_or_province.ilike(f"%{kw}%") for kw in keywords],
            *[Area.city_or_town.ilike(f"%{kw}%") for kw in keywords],
            *[Area.street.ilike(f"%{kw}%") for kw in keywords],
        )
        
        if seen_ids:
            where_conditions = and_(where_conditions, ~AssetRequest.id.in_(seen_ids))
        
        stmt = (
            select(AssetRequest)
            .join(Area)
            .where(where_conditions)
            .limit(limit)
        )
        results = (await db.execute(stmt)).scalars().all()
        return [{"type": "property-request", "id": r.id, "data": PropertyRequestSchema.from_orm_with_relations(r).model_dump()} for r in results]