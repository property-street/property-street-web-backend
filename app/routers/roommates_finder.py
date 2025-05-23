from redis.asyncio import Redis
from fastapi import APIRouter, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.database import get_db
from property_street_backend.app.initiator import get_redis
from property_street_backend.app.controllers.auth import decode_user_from_token, TokenData
from property_street_backend.app.controllers.roommate_finder.core import publish_roommate_finding
from property_street_backend.app.controllers.roommate_finder.schema import RoommateFinderRequestSchema

router = APIRouter(prefix='/roommate-finder', tags=['roommate-finder'])

@router.post('', status_code=status.HTTP_201_CREATED, response_description="Roommate finder request successfully published.")
async def request_rommmate_finder(
    data: RoommateFinderRequestSchema,
    requester: TokenData = Depends(decode_user_from_token),
    redis_client: Redis = Depends(get_redis), 
    db: AsyncSession = Depends(get_db)
):
    return await publish_roommate_finding(
        request_data = data.model_dump(),
        requester_id = requester.id,
        redis_client = redis_client,
        db = db
    )
