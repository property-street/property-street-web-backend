from redis.asyncio import Redis
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession


from .services import fetch_latest_assets
from property_street_backend.app.database import get_db
from property_street_backend.app.initiator import get_redis
from property_street_backend.app.schemas.asset_schemas import (
    LatestAssetsFetchResponseSchema,
)
from property_street_backend.log_config.logger_config import log_message


router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("/latest",response_model=LatestAssetsFetchResponseSchema)
async def recent_assets(
    session: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """
    Fetch paginated latest assets. Assets that fail schema validation are logged and skipped.
    """
    return await fetch_latest_assets(
        page = page,
        size = size,
        session = session,
        redis_client = redis_client
    )