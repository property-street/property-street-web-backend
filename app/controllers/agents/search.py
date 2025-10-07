from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import User

async def search_agents(query_data: dict, db: AsyncSession):
    keywords = query_data['keywords']
    if not keywords:
        return []
    stmt = (
        select(User)
        .where(User.user_role == 'agent')
        .where(or_(
            *[User.first_name.ilike(f"%{kw}%") for kw in keywords],
            *[User.last_name.ilike(f"%{kw}%") for kw in keywords],
        ))
        .limit(20)
    )
    results = (await db.execute(stmt)).scalars().all()
    return [{"type": "agent", "data": r} for r in results]
