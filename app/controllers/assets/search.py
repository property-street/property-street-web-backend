from typing import Dict, List, Any
from sqlalchemy import select, or_, false
from sqlalchemy.ext.asyncio import AsyncSession


from .models import Asset
from .schemas import (
    AssetResponseSchema,
    PropertySearchResponse,
)
from property_street_backend.app.models import (
    Tag,
    Area, 
)


async def search_assets(query_data: Dict[str, Any], db: AsyncSession) -> List[PropertySearchResponse]:
    keywords: List[str] = query_data.get('keywords', [])
    numbers: List[int] = query_data.get('numbers', [])

    if not keywords and not numbers:
        return []

    # -----------------------------
    # Build text search conditions
    # -----------------------------
    text_conditions = []
    for kw in keywords:
        like_pattern = f"%{kw}%"
        text_conditions.append(or_(
            Asset.title.ilike(like_pattern),
            Asset.description.ilike(like_pattern),
            Asset.category.ilike(like_pattern),
            Tag.name.ilike(like_pattern),
            # Area fields (no `name` in your model)
            Area.country.ilike(like_pattern),
            Area.state_or_province.ilike(like_pattern),
            Area.city_or_town.ilike(like_pattern),
            Area.street.ilike(like_pattern),
        ))

    # Combine conditions into a single OR
    where_clause = or_(*text_conditions)

    # -----------------------------
    # Build the base query
    # -----------------------------
    stmt = (
        select(Asset)
        .join(Area, Asset.area_id == Area.id)
        .join(Asset.tags, isouter=True)
        .where(where_clause)
        .distinct()
        .limit(20)
    )

    # -----------------------------
    # Execute the query
    # -----------------------------
    results = (await db.execute(stmt)).scalars().all()

    # -----------------------------
    # Optionally: Apply numeric filter for price proximity
    # -----------------------------
    if numbers:
        filtered = []
        for asset in results:
            price_val = float(asset.price or 0)
            for n in numbers:
                # Example: consider close prices within ₦200,000 difference
                if abs(price_val - n) < 200_000:
                    filtered.append(asset)
                    break
        results = filtered

    # -----------------------------
    # Return structured output
    # -----------------------------
    return [{"type": "property", "data": AssetResponseSchema.model_validate(asset).model_dump()} for asset in results]