import json
from fastapi import status
from sqlalchemy import select
from redis.asyncio import Redis
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import AssetResponseSchema
from property_street_backend.app.models import (
    User,
    Asset, 
    Agent, 
)
from property_street_backend.app.initiator import logger
from property_street_backend.config.settings import DEBUG
from property_street_backend.log_config.logger_config import log_message
from property_street_backend.app.controllers.activity import (
    auto_category_hset_key,
    newly_created_asset_set_key, 
)

def eager_asset_load():
    return (
        select(Asset)
        .options(
            selectinload(Asset.features),
            selectinload(Asset.tags),
            selectinload(Asset.area),
            selectinload(Asset.cloud_images),
            selectinload(Asset.agent)
            .selectinload(Agent.user)
            .selectinload(User.profile_avatar)

        )
    ) 


async def fetch_latest_assets(
    page: int,
    size: int,
    session: AsyncSession,
    redis_client: Redis
):
    offset = (page - 1) * size
    results = []

    # === Step 1: Try Redis Cache ===
    newly_created_asset_serialized_cache_dict = await redis_client.hget(
        auto_category_hset_key, newly_created_asset_set_key
    )

    newly_created_asset_cache_dict = (
        json.loads(newly_created_asset_serialized_cache_dict)
        if newly_created_asset_serialized_cache_dict
        else {}
    )
    if newly_created_asset_cache_dict:
        asset_list = list(newly_created_asset_cache_dict.values())
        asset_list.reverse()

        # Get portion from cache
        cache_slice = asset_list[offset:offset + size]
        results.extend(cache_slice)

    cache_result_length = len(results)
    size -= cache_result_length

    # === Step 2: Fill remaining slots from DB ===
    if size > 0:
        # db_offset = max(0, offset - len(asset_list))  # Adjust offset to avoid skipping
        db_offset = offset + cache_result_length  # Adjust offset to avoid skipping
        stmt = (
            eager_asset_load() # Eager load relationships
            .order_by(Asset.created_at.desc())
            .offset(db_offset)
            .limit(size)
        )
        result = await session.execute(stmt)
        raw_assets = result.scalars().all()
        results.extend(raw_assets)

    # === Step 3: Manual Schema Validation ===
    valid_assets = []
    skipped_assets = []

    try:
        for asset in results:
            try:
                if isinstance(asset, dict):
                    validated_asset = AssetResponseSchema.model_validate(asset)
                else:
                    validated_asset = AssetResponseSchema.model_validate(asset.__dict__)
                valid_assets.append(validated_asset)
            except ValidationError as ve:
                asset_id = getattr(asset, 'id', asset.get('id') if isinstance(asset, dict) else None)
                
                # refresh the asset
                try:
                    result = await session.execute(
                        eager_asset_load() # Eager load relationships
                        .where(Asset.id == asset_id)
                    )
                    refreshed_asset = result.scalars().one()
                    valid_assets.append(
                        AssetResponseSchema.model_validate(refreshed_asset)
                    )
                except:
                    skipped_assets.append(asset_id)
                
                    log_message(
                        log_type="error",
                        message=f"Asset ID {asset_id or 'unknown'} failed validation. Reason: {ve}"
                    )

    except Exception as e:
        f_message = "An error occurred while validating latest assets."
        d_message = f"{f_message} Reason: {e}"
        log_message(log_type="error", message=d_message)
        logger.error(d_message)
        raise HTTPException(status_code=500, detail=f_message)

    logger.info(
        f"{len(valid_assets)} valid assets returned. {len(skipped_assets)} skipped due to schema errors."
    )

    return {"assets": valid_assets}


async def fetch_agent_assets(
    session: AsyncSession,
    user: User,
    size: int,
    page: int,
):
    agent: Agent = user.agent_profile
    if not user.agent_profile:
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found"
            )
    
    agent_id = agent.id
    offset  = (page-1) * size

    try:
        # Query the agent and related assets
        query = await session.execute(
            eager_asset_load()
            .where(Asset.id == agent_id)
            .offset(offset)
            .limit(size)
        )
        return query.scalars().all()
    except Exception as e:
        f_message = "An error occured while retrieving your assets."
        d_message = f"An error occured while retrieving agent {agent_id} asset. Reason {e}" 
        logger.error(d_message)
        log_message('error', d_message)
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = f_message
        )