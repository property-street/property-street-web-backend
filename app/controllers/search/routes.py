from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession


from .services import global_search
from .schemas import SearchResultSchema, PaginatedSearchResultSchema
from property_street_backend.app.database import get_db


router = APIRouter(prefix='/search', tags=['search'])

@router.get('/{query}/', response_model=PaginatedSearchResultSchema)
async def get_results(
    query: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    seen_ids: Optional[str] = Query(None, description="Comma-separated list of IDs to exclude")
):
    seen_ids_list = []
    if seen_ids:
        seen_ids_list = [int(id) for id in seen_ids.split(',') if id.strip().isdigit()]
    
    return await global_search(query, limit=limit, offset=offset, seen_ids=seen_ids_list)
