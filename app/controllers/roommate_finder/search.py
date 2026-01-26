from typing import List
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import (
    RoommateFinderResponseSchema,
    RoommateRequestSearchResponse,
)
from property_street_backend.app.models import Area, RoommateFinder
from property_street_backend.config.postgres_connection_manager import runtime_async_session_maker

async def search_roommates(query_data: dict) -> List[RoommateRequestSearchResponse]:
    AsyncSessionLocal = runtime_async_session_maker()
    async with AsyncSessionLocal() as db:
        keywords = query_data['keywords']
        stmt = (
            select(RoommateFinder)
            .join(Area)
            .where(or_(
                *[RoommateFinder.extra_conditions.ilike(f"%{kw}%") for kw in keywords],
                *[RoommateFinder.category.ilike(f"%{kw}%") for kw in keywords],
                # Area fields
                *[Area.country.ilike(f"%{kw}%") for kw in keywords],
                *[Area.state_or_province.ilike(f"%{kw}%") for kw in keywords],
                *[Area.city_or_town.ilike(f"%{kw}%") for kw in keywords],
                *[Area.street.ilike(f"%{kw}%") for kw in keywords],
            ))
            .limit(20)
        )
        results = (await db.execute(stmt)).scalars().all()
        return [{"type": "roommates-finder", "data": RoommateFinderResponseSchema.from_orm_with_relations(r).model_dump()} for r in results]