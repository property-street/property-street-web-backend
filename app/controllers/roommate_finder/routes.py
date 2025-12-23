from typing import List
from redis.asyncio import Redis
from fastapi import APIRouter, status, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import User
from property_street_backend.app.database import get_db
from .services import (
    handle_my_requests,
    get_cached_roomies_application_ids,
    get_roommate_request_by_id,
)
from property_street_backend.app.initiator import get_redis
from .rf_application import roommates_finder_request_application
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
from .services import delete_roommate_request
from fastapi import Response


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
    '/my-requests', 
    status_code=status.HTTP_200_OK, 
    response_description="My requests retrieved.",
    response_model = List[RoommateFinderResponseSchema],
)
async def my_requests(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    requester: User = Depends(decode_user_from_token),
):
    return await handle_my_requests( page, size, session, requester )


@router.get(
    '/request-to-join/{request_id}', 
    status_code=status.HTTP_201_CREATED, 
    response_description="Roomie application executed.",
    response_model = List[int],
)
async def route_roommates_finder_request_application(
    request_id: int,
    session: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
    applicant: User = Depends(decode_user_from_token),
):
    return await roommates_finder_request_application(applicant, request_id, session, redis_client)


@router.get(
    '/cache-ids', 
    status_code=status.HTTP_200_OK, 
    response_model = List[int],
)
async def cache_ids(
    requester: User = Depends(decode_user_from_token),
):
    return await get_cached_roomies_application_ids(requester)


@router.delete(
    '/requests/{request_id}/',
    status_code=status.HTTP_204_NO_CONTENT,
    response_description="Roommate request deleted",
)
async def delete_request(
    request_id: int,
    session: AsyncSession = Depends(get_db),
    requester: User = Depends(decode_user_from_token),
):
    await delete_roommate_request(request_id=request_id, db=session, requester=requester)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    '/requests/{request_id}',
    status_code=status.HTTP_200_OK,
    response_description="Roommate request retrieved",
    response_model=RoommateFinderResponseSchema,
)
async def get_request_by_id(
    request_id: int,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(decode_user_from_token_optional),
):
    return await get_roommate_request_by_id(request_id=request_id, db=session)