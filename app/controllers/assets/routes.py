from typing import List
from fastapi import Query
import redis.asyncio as redis
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, status, HTTPException


from .services import (
    eager_asset_load,
    fetch_agent_assets,
    get_unverified_properties,
    update_verification_state,
)
from property_street_backend.app.database import get_db
from property_street_backend.app.initiator import (
    logger,
    get_redis,
)
from property_street_backend.config.settings import (
    DEBUG,
    NEWLY_CREATED_ASSET_TTL,
    TEST_NEWLY_CREATED_ASSET_TTL,
)
from property_street_backend.app.models import Asset, User
from property_street_backend.app.controllers.auth.services import (
    require_roles,
)
from property_street_backend.app.initiator import get_redis
from property_street_backend.app.controllers.assets.schemas import (
    AssetResponseSchema,
    ProcessAssetSchema
)
from property_street_backend.config import env_is_test
from property_street_backend.log_config.logger_config import log_message
from property_street_backend.app.controllers.activity.agent_crud_processing import (
    process_asset as controller_process_asset,
    remove_tags_from_asset,
)
from property_street_backend.app.controllers.assets.services import fetch_latest_assets


router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("/latests", response_model=List[AssetResponseSchema])
async def latest(
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


@router.post("/process-asset", status_code=status.HTTP_200_OK)
async def process_asset(
    data: ProcessAssetSchema, 
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    user: User = Depends(require_roles("agent", "staff", "admin"))
):
    request_data: dict = data.model_dump()
    
    try:
        # check if the tags to remove is present
        tags_to_remove_object = request_data.get('tags_to_remove_object')
        if tags_to_remove_object:
            await remove_tags_from_asset(
                session = db,
                asset_id = tags_to_remove_object['asset_id'],
                tag_ids=tags_to_remove_object['tag_ids']
            )
        
        # check for asset data to process
        asset_data_to_process = request_data.get('asset_data_to_process')
        if asset_data_to_process:
            processed_asset = await controller_process_asset(
                data_to_be_processed = asset_data_to_process,
                db = db,
                redis_client = redis_client,
                ttl_in_seconds = request_data.get(
                    'ttl',
                    (TEST_NEWLY_CREATED_ASSET_TTL 
                        if env_is_test() else 
                    NEWLY_CREATED_ASSET_TTL)
                ),
                agent = user
            )
            if processed_asset:
                schematized_asset = AssetResponseSchema.model_validate(processed_asset)
                schematized_asset_to_dict = schematized_asset.model_dump()
                return schematized_asset_to_dict

        
        s_message=f'Asset processed successfully.'
        # log the error
        log_message(
            log_type='success',
            message=s_message
        )
        if DEBUG:
            logger.info(s_message)
    except Exception as e:
        e_message=f'An error occured on processing of asset. Reason: {e}'
        # log the error
        log_message(
            log_type='error',
            message=e_message
        )
        if DEBUG:
            logger.error(e_message)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occured on processing of asset"
        )


@router.get("/agent-assets/{agent_id}", response_model=List[AssetResponseSchema])
async def retrieve_agent_assets(
    agent_id: int,
    session: AsyncSession = Depends(get_db),
    # _: User = Depends(decode_user_from_token),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    return await fetch_agent_assets(
        session = session,
        agent_id = agent_id,
        page = page,
        size = size
    )
    

@router.get("/my-properties", response_model=List[AssetResponseSchema])
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
        size = size
    )
    

@router.get("/{asset_id}", response_model=AssetResponseSchema)
async def fetch_asset_by_id(
    asset_id: int,  # Accept asset ID as a path parameter
    session: AsyncSession = Depends(get_db),
):
    """
    Fetches a single asset by its ID.
    """
    # Explicitly handle the 404 logic outside the try block
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


@router.get("/unverified-properties/", response_model=List[AssetResponseSchema])
async def unverified_properties(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles('admin','staff')),
):
    return await get_unverified_properties(db,page,size)


@router.post("/confirm-verification/{asset_id}/", response_model=AssetResponseSchema)
async def confirm_verification(
    asset_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles('admin','staff')),
):
    """Mark the property as verified (admin only)."""
    return await update_verification_state(asset_id, db, 'verify')


@router.post("/cancel-verification/{asset_id}/", response_model=AssetResponseSchema)
async def cancel_verification_route(
    asset_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles('admin')),
):
    """Cancel a property's verification (admin only)."""
    return await update_verification_state(asset_id, db, 'cancel')