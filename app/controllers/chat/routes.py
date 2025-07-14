from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession


from property_street_backend.app.models import User
from .get_threads_schemas import ThreadSummarySchema
from .services import get_threads_with_latest_message
from property_street_backend.app.database import get_db
from property_street_backend.app.controllers.auth.services import decode_user_from_token


router = APIRouter(prefix='/chat', tags=['chat'])


@router.get('/get_threads_meta', response_model=List[ThreadSummarySchema])
async def threads_meta_getter(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(decode_user_from_token),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    return await get_threads_with_latest_message(
        db = session,
        user_id = user.id,
        page = page,
        page_size = size
    )