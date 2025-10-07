from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession


from .services import global_search
from .schemas import SearchResultSchema
from property_street_backend.app.database import get_db


router = APIRouter(prefix='/search', tags=['search'])

@router.get('/{query}/', response_model=List[SearchResultSchema])
async def get_results(
    query: str,
    db: AsyncSession = Depends(get_db),
):
    return await global_search(query,db)
