from typing import List
from redis.asyncio import Redis
from fastapi import APIRouter, status, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import User
from property_street_backend.app.database import get_db
from .services import (
    roommates_finder_request_application,
    get_cached_roomies_application_ids
)
from property_street_backend.app.initiator import get_redis
from property_street_backend.app.controllers.auth.services import (
    decode_user_from_token, 
    decode_user_from_token_optional,
)
from .schemas import (
    RFRSListWithCachedIds,
    RoommateFinderRequestSchema,
    RoommateFinderResponseSchema,
)
from .core import publish_roommate_finding
from .fetch_latest_requests import fetch_recent_roommate_finder_request


router = APIRouter(prefix='/roommate-finder', tags=['roommate-finder'])

@router.post(
    '', 
    status_code=status.HTTP_201_CREATED, 
    response_description="Roommate finder request successfully published.",
    response_model=RoommateFinderResponseSchema,
)
async def request_rommmate_finder(
    data: RoommateFinderRequestSchema,
    requester: User = Depends(decode_user_from_token),
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
    response_model = RFRSListWithCachedIds,
)
async def retrieve_latest_roommates_finder_requests(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    requester: User = Depends(decode_user_from_token_optional),
):
    return await fetch_recent_roommate_finder_request(
        page = page,
        size = size,
        session = session,
        requester = requester
    )

@router.get(
    '/request-to-join/{request_id}', 
    status_code=status.HTTP_201_CREATED, 
    response_description="Roomie application executed.",
    response_model = List[int],
)
async def route_roommates_finder_request_application(
    request_id: int,
    session: AsyncSession = Depends(get_db),
    applicant: User = Depends(decode_user_from_token),
):
    return await roommates_finder_request_application(applicant, request_id, session)


@router.get(
    '/cache-ids', 
    status_code=status.HTTP_200_OK, 
    response_model = List[int],
)
async def cache_ids(
    requester: User = Depends(decode_user_from_token),
):
    return await get_cached_roomies_application_ids(requester)