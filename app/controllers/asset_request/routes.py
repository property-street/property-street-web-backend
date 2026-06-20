from typing import List, Optional
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, status, Depends, Query

from .search import search_asset_requests
from .schemas import (
    DiscoverResponse,
    RequestResolution,
    AssetRequestResponseSchema,
)
from property_street_backend.app.database import get_db
from property_street_backend.app.initiator import get_redis
from property_street_backend.app.controllers.actors.models import User
from property_street_backend.app.schemas.auth_schemas import TokenData
from property_street_backend.app.controllers.auth.services import decode_user_from_token_optional
from property_street_backend.app.controllers.search.tools import normalize_query
from property_street_backend.app.controllers.auth.services import decode_user_from_token
from property_street_backend.app.controllers.asset_request.schemas import AssetRequestSchema
from .services import (
    fetch_recent_asset_request,
    handle_resolve_property_request,
    fetch_self_requests,
    discover_asset_requests,
)
from property_street_backend.app.controllers.asset_request.handle_asset_request import handle_asset_request


router = APIRouter(prefix="/asset-requests", tags=["asset-request"])

@router.post(
    "", 
    status_code=status.HTTP_201_CREATED, 
    response_model=AssetRequestResponseSchema, 
    response_description="Successful asset request."
)
async def asset_request_handler(
    data: AssetRequestSchema, 
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
    current_user: User = Depends(decode_user_from_token),
):
    return await handle_asset_request(
        requester = current_user,
        db = db,
        redis_client =  redis_client,
        request_data = data.model_dump()
    )


@router.get("/latests",response_model=List[AssetRequestResponseSchema])
async def recent_assets(
    session: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """
    Fetch paginated latest asset requests. Assets requests that fail schema validation are logged and skipped.
    """
    return await fetch_recent_asset_request(
        page = page,
        size = size,
        session = session,
    )

@router.get("/my-requests",response_model=List[AssetRequestResponseSchema])
async def recent_assets(
    session: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(decode_user_from_token),
):
    """
    Fetch paginated latest asset requests. Assets requests that fail schema validation are logged and skipped.
    """
    return await fetch_self_requests(
        page = page,
        size = size,
        session = session,
        user_id = current_user.id
    )

@router.get("/search/{query}")
async def search_property_request_endpoint(
    query: str,
    session: AsyncSession = Depends(get_db),
):      
    normalized_query = normalize_query(query)
    return await search_asset_requests(normalized_query,session)


@router.get("/discover", response_model=DiscoverResponse)
async def discover_asset_requests_endpoint(
    session: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(decode_user_from_token_optional),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    query: Optional[str] = Query(None),
    area: Optional[str] = Query(None),
    seen_ids: Optional[str] = Query(None),
):
    return await discover_asset_requests(
        session=session,
        user=user,
        page=page,
        size=size,
        query=query,
        area=area,
        seen_ids=seen_ids,
    )

@router.post("/resolve/{id}/", response_model=AssetRequestResponseSchema)
async def resolve_property_request(
    id: int,
    data: RequestResolution,
    session: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
    agent: User = Depends(decode_user_from_token),
):      
    return await handle_resolve_property_request(id, agent, redis_client, session, data.property_id, data.property)