from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, Query, HTTPException , status


from property_street_backend.app.models import User
from property_street_backend.app.database import get_db
from property_street_backend.app.initiator import logger
from .services import get_threads_with_latest_message, get_messages
from property_street_backend.log_config.logger_config import log_message
from .get_threads_schemas import ThreadSummarySchema, MessageSummarySchema
from property_street_backend.app.controllers.auth.services import decode_user_from_token


router = APIRouter(prefix='/chat', tags=['chat'])


@router.get('/get-threads-meta', response_model=List[ThreadSummarySchema])
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


@router.get('/get-messages/{participant_id}', response_model=List[MessageSummarySchema])
async def messages_getter(
    participant_id: int,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(decode_user_from_token),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    try:
        return await get_messages(
            db = session,
            participant_id = participant_id,
            host_id = user.id,
            page = page,
            size = size
        )
    except Exception as e:
        logger.error(e)
        log_message('error',e)
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = f"An error occured while retrieving chat for user {participant_id}"
        )