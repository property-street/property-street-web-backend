from typing import List
from fastapi import Query, Depends, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import User
from property_street_backend.app.database import get_db
from property_street_backend.app.controllers.assets.schemas import (
    PropertyResponseSchema,
    PartialPropertyResponseSchema,
)
from property_street_backend.app.controllers.assets.services import (
    handle_get_all_properties,
    get_unverified_properties,
    handle_get_all_verified_properties,
)
from property_street_backend.app.controllers.auth.services import (
    require_roles,
)

router = APIRouter(prefix="/properties", tags=["Admin Properties"])

@router.get("/all/", response_model=List[PartialPropertyResponseSchema])
async def get_all_properties_for_admin(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("staff", "admin")),
):
    return await handle_get_all_properties(
        session, page = page, size = size
    )

@router.get("/unverified/", response_model=List[PartialPropertyResponseSchema])
async def get_all_properties(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("staff", "admin")),
):
    return await get_unverified_properties(
        session, page = page, size = size
    )

@router.get("/verified/", response_model=List[PropertyResponseSchema])
async def get_all_unverified_properties(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("staff", "admin")),
):
    return await handle_get_all_verified_properties(
        session, page = page, size = size
    )