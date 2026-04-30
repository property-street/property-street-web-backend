from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.controllers.actors.models import User
from property_street_backend.app.controllers.auth.services import decode_user_from_token
from property_street_backend.app.controllers.token_management.services import (
    list_user_sessions,
    revoke_all_user_tokens,
    revoke_refresh_token,
)
from property_street_backend.app.database import get_db

router = APIRouter(prefix="/token-management", tags=["token-management"])


@router.get("/sessions")
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(decode_user_from_token),
):
    return await list_user_sessions(db, user)


@router.post("/revoke/refresh/{token_id}")
async def revoke_refresh(
    token_id: int = Path(..., description="ID of the refresh session to revoke"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(decode_user_from_token),
):
    return await revoke_refresh_token(db, user, token_id)


@router.post("/revoke/all")
async def revoke_all(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(decode_user_from_token),
):
    return await revoke_all_user_tokens(db, user)
