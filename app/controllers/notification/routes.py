from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, Query, HTTPException , status

from .schemas import NotificationResponse
from .services import get_all_notification
from property_street_backend.app.models import User
from property_street_backend.app.database import get_db
from property_street_backend.app.initiator import logger
from property_street_backend.log_config.logger_config import log_message
from property_street_backend.app.controllers.auth.services import decode_user_from_token


router = APIRouter(prefix='/notification', tags=['notification'])


@router.get('/', response_model=List[NotificationResponse]|[])
async def get_all_notification_endpoint(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(decode_user_from_token),
):
    return await get_all_notification(db,user.id)
    