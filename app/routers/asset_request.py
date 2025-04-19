from fastapi import APIRouter, status, Depends

from property_street_backend.app.database import get_db
from property_street_backend.app.initiator import get_redis_client
from property_street_backend.app.schemas.auth_schemas import TokenData
from property_street_backend.app.controllers.auth import decode_user_from_token
from property_street_backend.app.controllers.asset_request.schemas import AssetRequestSchema
from property_street_backend.app.controllers.asset_request.handle_asset_request import handle_asset_request

router = APIRouter(prefix='/asset_request', tag=['asset-request'])

router.post('', status_code=status.HTTP_201_CREATED)
async def asset_request_handler(
    data: AssetRequestSchema, 
    db = Depends(get_db),
    redis_client = Depends(get_redis_client),
    current_user:TokenData = Depends(decode_user_from_token),
):
    return handle_asset_request(
        requester_id = current_user.id,
        db = db,
        redis_client =  redis_client,
        request_data = data
    )