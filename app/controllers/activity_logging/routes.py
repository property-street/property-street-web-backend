from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.controllers.actors.models import User
from property_street_backend.app.controllers.auth.services import decode_user_from_token
from property_street_backend.app.controllers.activity_logging.enums import ActivityStatusChoice
from property_street_backend.app.controllers.activity_logging.schemas import (
    ActivityLogListResponseSchema,
    ActivityStatisticsSchema,
)
from property_street_backend.app.controllers.activity_logging.services import (
    get_activity_statistics,
    get_user_activities,
)
from property_street_backend.app.database import get_db

router = APIRouter(prefix="/activity-logs", tags=["activity-logs"])


@router.get("/my-activities/", response_model=ActivityLogListResponseSchema)
async def get_my_activities(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: ActivityStatusChoice = Query(None),
    days: int = Query(None, ge=1),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(decode_user_from_token),
):
    offset = (page - 1) * size
    activities, total = await get_user_activities(
        db, user, limit=size, offset=offset, status_filter=status, days=days
    )
    return {
        "total": total,
        "count": len(activities),
        "page": page,
        "size": size,
        "items": activities,
    }


@router.get("/statistics/", response_model=ActivityStatisticsSchema)
async def get_activity_stats(
    days: int = Query(None, ge=1),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(decode_user_from_token),
):
    return await get_activity_statistics(db, user, days=days)
