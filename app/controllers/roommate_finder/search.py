from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import Area, RoommateFinder

async def search_roommates(query_data: dict, db: AsyncSession):
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
    return [{"type": "roommates_finder", "data": r} for r in results]