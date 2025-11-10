from redis.asyncio import Redis
from fastapi import APIRouter, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession


from .models import User
from property_street_backend.app.database import get_db
from property_street_backend.app.initiator import get_redis
from .services import send_staff_invite_link, accept_staff_invite
from property_street_backend.app.controllers.auth.services import require_roles


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