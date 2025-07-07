from fastapi import APIRouter, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from .schemas import AssetRequestResponseSchema
from property_street_backend.app.database import get_db
from property_street_backend.app.initiator import get_redis
from property_street_backend.app.schemas.auth_schemas import TokenData
from property_street_backend.app.controllers.auth import decode_user_from_token
from property_street_backend.app.controllers.asset_request.schemas import AssetRequestSchema
from property_street_backend.app.controllers.asset_request.handle_asset_request import handle_asset_request

router = APIRouter(prefix="/asset-request", tags=["asset-request"])

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
    current_user:TokenData = Depends(decode_user_from_token),
):
    return await handle_asset_request(
        requester = current_user,
        db = db,
        redis_client =  redis_client,
        request_data = data.model_dump()
    )