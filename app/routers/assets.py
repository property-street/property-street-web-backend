from fastapi import Query
import redis.asyncio as redis
from redis.asyncio import Redis
from typing import Dict, Optional
from pydantic import ValidationError
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, status, HTTPException

from property_street_backend.app.models import Asset
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
from property_street_backend.app.controllers.auth import (
    decode_user_from_token,
    decode_user_from_token_optional,
)
from property_street_backend.app.initiator import get_redis
from property_street_backend.app.schemas.auth_schemas import (
    TokenData, 
)
from property_street_backend.app.schemas.asset_schemas import (
    LatestAssetsFetchResponseSchema,
    AssetFetchByIdResponseSchema 
)
from property_street_backend.app.controllers.assets.schemas import (
    AssetFetchResponseSchema,
    AssetFetchResponseSchema
)
from property_street_backend.config import env_is_test
from property_street_backend.log_config.logger_config import log_message
from property_street_backend.app.controllers.activity.agent_crud_processing import (
    process_asset as controller_process_asset,
    remove_tags_from_asset,
)
from property_street_backend.app.controllers.assets.services import fetch_latest_assets
from property_street_backend.app.controllers.activity.agent_assets_retrieval import get_agent_assets


router = APIRouter(prefix="/assets", tags=["assets"])


@router.post("/process-asset", status_code=status.HTTP_200_OK)
async def process_asset(
    data: Dict, 
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    _: TokenData = Depends(decode_user_from_token)
):
    try:
        # check if the tags to remove is present
        tags_to_remove_object = data.get('tags_to_remove_object')
        if tags_to_remove_object:
            await remove_tags_from_asset(
                session = db,
                asset_id = tags_to_remove_object['asset_id'],
                tag_ids=tags_to_remove_object['tag_ids']
            )
        
        # check for asset data to process
        asset_data_to_process = data.get('asset_data_to_process')
        if asset_data_to_process:
            processed_asset = await controller_process_asset(
                data_to_be_processed = asset_data_to_process,
                db = db,
                redis_client = redis_client,
                ttl_in_seconds=data.get(
                    'ttl',
                    (TEST_NEWLY_CREATED_ASSET_TTL 
                        if env_is_test() else 
                    NEWLY_CREATED_ASSET_TTL)
                )
            )
            if processed_asset:
                schematized_asset = AssetFetchResponseSchema.model_validate(processed_asset)
                schematized_asset_to_dict = schematized_asset.model_dump()
                return {"data" : schematized_asset_to_dict}

        
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
    
    
@router.get("/fetch_agent_assets")
async def fetch_agent_assets(
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(decode_user_from_token)
):
    try:
        # get the authenticated user's agent profile
        agent = current_user.agent_profile

        if not agent:
            # log the error
            log_message(
                log_type='error',
                message='Agent not found'
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found"
            )
        
        # log the error
        log_message(
            log_type='success',
            message=f'Asset fetched successfully.'
        )
        
        return await get_agent_assets(
            db = db,
            agent_id = agent.id
        )
    except Exception as e:
        # log the error
        log_message(
            log_type='error',
            message=f'An error occured on retrieval of agent data. Reason: {e}'
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occured on retrieval of agent data."
        )


@router.get("/assets/{asset_id}",response_model=AssetFetchByIdResponseSchema)
async def fetch_asset_by_id(
    asset_id: int,  # Accept asset ID as a path parameter
    session: AsyncSession = Depends(get_db),
    current_user: Optional[TokenData] = Depends(decode_user_from_token_optional)
):
    """
    Fetches a single asset by its ID.
    Includes user authentication status in the response.
    """
    # Explicitly handle the 404 logic outside the try block
    stmt = select(Asset).filter(Asset.id == asset_id)
    result = await session.execute(stmt)
    asset = result.scalars().first()

    if not asset:
        log_message(
            log_type="error",
            message=f"Asset with ID {asset_id} not found"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with ID {asset_id} not found"
        )

    try:
        # Determine user status
        is_authenticated = current_user is not None
        user_details = (
            {
                "first_name": current_user.first_name,
                "client_is_agent": True if current_user.agent_profile else False
            }
            if is_authenticated else {}
        )

        log_message(
            log_type="success",
            message=f"Asset with ID {asset_id} successfully retrieved"
        )

        # Return asset and user authentication status
        return {
            "asset": asset,
            "is_authenticated": is_authenticated,
            **user_details,
        }

    except Exception as e:
        log_message(
            log_type="error",
            message=f"An unexpected error occurred while retrieving asset ID {asset_id}. Reason: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again later."
        )