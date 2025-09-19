from fastapi import (
    status,
    Depends,
    APIRouter, 
)
import redis.asyncio as redis
from typing import Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.config.settings import (
    SEARCH_UNIT_TTL
)
from property_street_backend.app.database import get_db
from property_street_backend.app.initiator import get_redis
from property_street_backend.app.controllers.search.search_string_processor import (
    process_search_entries,
)
from property_street_backend.app.schemas.auth_schemas import (
    TokenData, 
)


router = APIRouter(prefix="/search", tags=["search"])

@router.post("", status_code=status.HTTP_200_OK)
async def test_search_endpoint_handler(
    data: Dict,
    session: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
):
    await process_search_entries(
        entries=data.get('entries'),
        redis_client=redis_client,
        db_session=session,
        expiry_seconds=data.get('ttl',SEARCH_UNIT_TTL)
    )