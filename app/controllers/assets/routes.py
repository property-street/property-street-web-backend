from typing import List, Optional
from fastapi import Query
import redis.asyncio as redis
from redis.asyncio import Redis
from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, status, HTTPException

from .schemas import (
    StreamPayload,
    StreamResponse,
    PropertySchema,
    InteractionEvents,
    PatchPropertySchema,
    PropertyResponseSchema,
    PropertyInteractionSchema,
)
from .services import (
    handle_stream,
    eager_asset_load,
    fetch_agent_assets,
    handle_delete_property,
    get_unverified_properties,
    update_verification_state,
    handle_persist_property_interaction,
)
from property_street_backend.app.database import get_db
from property_street_backend.app.initiator import (
    logger,
    get_redis,
)
from property_street_backend.app.models import Asset, User
from property_street_backend.app.controllers.auth.services import (
    require_roles,
    decode_user_from_token,
    decode_user_from_token_optional,
)
from .property_processor_utils import handle_property_create_update
# from property_street_backend.log_config.logger_config import log_message
from property_street_backend.app.controllers.assets.services import fetch_latest_assets
from datetime import datetime
from sqlalchemy import select, and_

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("/latests", response_model=List[PropertyResponseSchema])
async def latest(
    session: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
    user: Optional[User] = Depends(decode_user_from_token_optional),
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
        redis_client = redis_client,
        user = user,
    )


@router.post("/create-property", status_code=status.HTTP_201_CREATED, response_model=PropertyResponseSchema)
async def create_property_endpoint(
    data: PropertySchema, 
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    agent: User = Depends(require_roles("agent", "staff", "admin"))
):
    return await handle_property_create_update(data, db, redis_client, agent)


@router.patch("/{id}", status_code=status.HTTP_200_OK, response_model=PropertyResponseSchema)
async def update_property_endpoint(
    data: PatchPropertySchema, 
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    agent: User = Depends(require_roles("agent", "staff", "admin"))
):
    return await handle_property_create_update(data, db, redis_client, agent, newly_created=False)


@router.get("/agent-assets/{agent_id}", response_model=List[PropertyResponseSchema])
async def retrieve_agent_assets(
    agent_id: int,
    session: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(decode_user_from_token_optional),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    return await fetch_agent_assets(
        session = session,
        agent_id = agent_id,
        page = page,
        size = size,
        user = user,
    )
    

@router.get("/my-properties", response_model=List[PropertyResponseSchema])
async def retrieve_agent_assets(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("agent", "staff", "admin")),
):
    return await fetch_agent_assets(
        session = session,
        agent_id = current_user.id,
        page = page,
        size = size,
        user = current_user,
    )
    

@router.get("/{asset_id}", response_model=PropertyResponseSchema)
async def fetch_asset_by_id(
    asset_id: int,  # Accept asset ID as a path parameter
    session: AsyncSession = Depends(get_db),
):
    """
    Fetches a single asset by its ID.
    """
    result = await session.execute(
        eager_asset_load()
        .where(Asset.id == asset_id)
    )
    asset = result.scalars().first()
    
    if not asset:
        logger.error(
            f"Asset with ID {asset_id} not found"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with ID {asset_id} not found"
        )
    
    return asset


@router.get("/unverified-properties/", response_model=List[PropertyResponseSchema])
async def unverified_properties(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles('admin','staff')),
):
    return await get_unverified_properties(db,page,size)


@router.post("/confirm-verification/{asset_id}/", response_model=PropertyResponseSchema)
async def confirm_verification(
    asset_id: int,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
    _: User = Depends(require_roles('admin','staff')),
):
    """Mark the property as verified (admin only)."""
    return await update_verification_state(asset_id, db, redis_client, 'verify')


@router.post("/cancel-verification/{asset_id}/", response_model=PropertyResponseSchema)
async def cancel_verification_route(
    asset_id: int,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
    _: User = Depends(require_roles('admin','staff')),
):
    """Cancel a property's verification (admin only)."""
    return await update_verification_state(asset_id, db, redis_client, 'cancel')


@router.delete("/delete/{property_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property(
    property_id: int,
    db: AsyncSession = Depends(get_db),
    agent: User = Depends(require_roles('admin','staff','agent')),
):
    """Delete property."""
    return await handle_delete_property(db, property_id, agent)


@router.post("/stream/", response_model=StreamResponse)
async def stream_property(
    data: StreamPayload,
    size: int = Query(5, ge=1, le=100),
    user: User = Depends(decode_user_from_token_optional),
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
):
    return await handle_stream(user, size, db, redis_client, data)


@router.post("/persist-interaction/")
async def persist_property_interaction(
    data: InteractionEvents,
    user: User = Depends(decode_user_from_token),
    db: AsyncSession = Depends(get_db),
):
    return await handle_persist_property_interaction(data, user, db)