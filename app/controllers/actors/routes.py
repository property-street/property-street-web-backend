from redis.asyncio import Redis
from fastapi import APIRouter, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession


from .models import User
from property_street_backend.app.database import get_db
from property_street_backend.app.initiator import get_redis
from app.controllers.assets.schemas import (
    CloudImageSchema, 
    CloudImageResponseSchema,
)
from .services import (
    accept_staff_invite,
    send_staff_invite_link,
    handle_update_profile_avatar,
)
from property_street_backend.app.controllers.auth.services import (
    require_roles,
    decode_user_from_token,
)


router = APIRouter(prefix="/actors")


@router.post('/generate-staff-invite-link/{client_id}/', status_code=status.HTTP_201_CREATED)
async def generate_staff_invite_link(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
    _: User = Depends(require_roles('admin'))
):
    return await send_staff_invite_link(client_id, db, redis_client)


@router.post('/validate-staff-invite/{token}/')
async def validate_staff_invite(
    token: str,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
):
    return await accept_staff_invite(token, db, redis_client)


@router.patch('/update-profile-avatar/', response_model=CloudImageResponseSchema)
async def update_profile_avatar(
    data: CloudImageSchema,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(decode_user_from_token)
):
    return await handle_update_profile_avatar(db, user, data.model_dump(exclude_none=True))