from typing import List
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import (
    RoommateFinderResponseSchema,
    RoommateRequestSearchResponse,
)
from property_street_backend.app.models import Area, RoommateFinder
from property_street_backend.config.postgres_connection_manager import runtime_async_session_maker

async def search_roommates(query_data: dict, limit: int = 20, seen_ids: List[int] = None) -> List[RoommateRequestSearchResponse]:
    if seen_ids is None:
        seen_ids = []
        
    AsyncSessionLocal = runtime_async_session_maker()
    async with AsyncSessionLocal() as db:
        keywords = query_data['keywords']
        
        where_conditions = or_(
            *[RoommateFinder.extra_conditions.ilike(f"%{kw}%") for kw in keywords],
            *[RoommateFinder.category.ilike(f"%{kw}%") for kw in keywords],
            # Area fields
            *[Area.country.ilike(f"%{kw}%") for kw in keywords],
            *[Area.state_or_province.ilike(f"%{kw}%") for kw in keywords],
            *[Area.city_or_town.ilike(f"%{kw}%") for kw in keywords],
            *[Area.street.ilike(f"%{kw}%") for kw in keywords],
        )
        
        if seen_ids:
            where_conditions = and_(where_conditions, ~RoommateFinder.id.in_(seen_ids))
        
        stmt = (
            select(RoommateFinder)
            .join(Area)
            .where(where_conditions)
            .limit(limit)
        )
        results = (await db.execute(stmt)).scalars().all()
        return [{"type": "roommates-finder", "id": r.id, "data": RoommateFinderResponseSchema.from_orm_with_relations(r).model_dump()} for r in results]