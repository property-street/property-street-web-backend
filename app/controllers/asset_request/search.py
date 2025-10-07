from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from .models import AssetRequest
from property_street_backend.app.models import Area

async def search_asset_requests(query_data: dict, db: AsyncSession):
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
    return [{"type": "asset_request", "data": r} for r in results]