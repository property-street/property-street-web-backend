from typing import List
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import AgentSearchResponseSchema
from property_street_backend.app.models import User
from property_street_backend.app.controllers.actors.schemas import AgentResponseSchema
from property_street_backend.config.postgres_connection_manager import runtime_async_session_maker


async def search_agents(query_data: dict, limit: int = 20, seen_ids: List[int] = None) -> List[AgentSearchResponseSchema]:
    if seen_ids is None:
        seen_ids = []
        
    AsyncSessionLocal = runtime_async_session_maker()
    async with AsyncSessionLocal() as db:
        keywords = query_data['keywords']
        if not keywords:
            return []
        
        where_conditions = or_(
            *[User.username.ilike(f"%{kw}%") for kw in keywords],
            *[User.first_name.ilike(f"%{kw}%") for kw in keywords],
            *[User.last_name.ilike(f"%{kw}%") for kw in keywords],
        )
        
        if seen_ids:
            where_conditions = and_(where_conditions, ~User.id.in_(seen_ids))
        
        stmt = (
            select(User)
            .where(User.user_role == 'agent')
            .where(where_conditions)
            .limit(limit)
        )
        results = (await db.execute(stmt)).scalars().all()
        return [{"type": "agent", "id": r.id, "data": AgentResponseSchema.model_validate(r).model_dump()} for r in results]
