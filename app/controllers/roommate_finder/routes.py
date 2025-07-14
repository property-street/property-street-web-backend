from typing import List
from redis.asyncio import Redis
from fastapi import APIRouter, status, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.database import get_db
from property_street_backend.app.initiator import get_redis
from property_street_backend.app.controllers.auth.services import decode_user_from_token, TokenData
from property_street_backend.app.controllers.roommate_finder.core import publish_roommate_finding
from property_street_backend.app.controllers.roommate_finder.schemas import (
    RoommateFinderRequestSchema,
    RoommateFinderResponseSchema
)
from property_street_backend.app.controllers.roommate_finder.fetch_latest_requests import fetch_recent_roommate_finder_request


router = APIRouter(prefix='/roommate-finder', tags=['roommate-finder'])

@router.post(
    '', 
    status_code=status.HTTP_201_CREATED, 
    response_description="Roommate finder request successfully published.",
    response_model=RoommateFinderResponseSchema,
)
async def request_rommmate_finder(
    data: RoommateFinderRequestSchema,
    requester: TokenData = Depends(decode_user_from_token),
    redis_client: Redis = Depends(get_redis), 
    db: AsyncSession = Depends(get_db)
):
    return await publish_roommate_finding(
        request_data = data.model_dump(),
        requester = requester,
        redis_client = redis_client,
        db = db
    )

@router.get(
    '/latests', 
    status_code=status.HTTP_200_OK, 
    response_description="Latest Roommate finder requests retrieved.",
    response_model = List[RoommateFinderResponseSchema],
)
async def retrieve_latest_roommates_finder_requests(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    _: TokenData = Depends(decode_user_from_token),
    db: AsyncSession = Depends(get_db)
):
    return await fetch_recent_roommate_finder_request(
        page = page,
        size = size,
        db = db
    )
