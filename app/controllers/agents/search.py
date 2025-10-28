from typing import List
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import AgentSearchResponseSchema
from property_street_backend.app.models import User
from property_street_backend.app.controllers.actors.schemas import AgentResponseSchema

async def search_agents(query_data: dict, db: AsyncSession) -> List[AgentSearchResponseSchema]:
    keywords = query_data['keywords']
    if not keywords:
        return []
    stmt = (
        select(User)
        .where(User.user_role == 'agent')
        .where(or_(
            *[User.username.ilike(f"%{kw}%") for kw in keywords],
            *[User.first_name.ilike(f"%{kw}%") for kw in keywords],
            *[User.last_name.ilike(f"%{kw}%") for kw in keywords],
        ))
        .limit(20)
    )
    results = (await db.execute(stmt)).scalars().all()
    return [{"type": "agent", "data": AgentResponseSchema.model_validate(r).model_dump()} for r in results]
