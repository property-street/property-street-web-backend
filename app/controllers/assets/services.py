import json
from fastapi import status
from sqlalchemy import and_
from redis.asyncio import Redis
from typing import List, Literal
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from .schemas import AssetResponseSchema
from property_street_backend.app.models import (
    User,
    Asset, 
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
            selectinload(Asset.cover_image),
            selectinload(Asset.agent)
            .selectinload(User.profile_avatar)
        )
    )


async def validate_assets(
    session: AsyncSession, 
    assets: list[Asset],
):
    valid_assets = []
    skipped_assets = []

    for asset in assets:
        try:
            validated_asset = AssetResponseSchema.model_validate(asset)
            valid_assets.append(validated_asset)
        except ValidationError as ve:
            asset_id = getattr(asset, 'id', asset.get('id') if isinstance(asset, dict) else None)

            # refresh the asset
            try:
                result = await session.execute(
                    eager_asset_load().where(Asset.id == asset_id)
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
    
    return valid_assets, skipped_assets


async def fetch_latest_assets(
    page: int,
    size: int,
    session: AsyncSession,
    redis_client: Redis
):
    offset = (page - 1) * size
    results = []
    seen_ids = set()  # Track IDs to avoid duplication

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

        # Record their IDs to skip in DB fetch
        for asset in cache_slice:
            if isinstance(asset, dict):
                seen_ids.add(asset.get("id"))
            else:
                seen_ids.add(getattr(asset, "id", None))

    cache_result_length = len(results)
    size -= cache_result_length

    # === Step 2: Fill remaining slots from DB ===
    if size > 0:
        db_offset = offset + cache_result_length
        stmt = (
            eager_asset_load()
            .order_by(Asset.created_at.desc())
            .offset(db_offset)
            .limit(size)
        )

        # Skip already retrieved IDs
        if seen_ids:
            stmt = stmt.where(~Asset.id.in_(seen_ids))

        result = await session.execute(stmt)
        raw_assets = result.scalars().all()
        results.extend(raw_assets)

    # === Step 3: Manual Schema Validation ===
    try:
        valid_assets, skipped_assets = await validate_assets(session, results)
    except Exception as e:
        f_message = "An error occurred while validating latest assets."
        d_message = f"{f_message} Reason: {e}"
        log_message(log_type="error", message=d_message)
        logger.error(d_message)
        raise HTTPException(status_code=500, detail=f_message)

    logger.info(
        f"{len(valid_assets)} valid assets returned. {len(skipped_assets)} skipped due to schema errors."
    )

    return valid_assets



async def fetch_agent_assets(
    session: AsyncSession,
    size: int,
    page: int,
    agent_id: int,
):
    offset  = (page-1) * size
    # Query the agent and related assets
    query = await session.execute(
        eager_asset_load()
        .where(Asset.agent_id == agent_id)
        .offset(offset)
        .limit(size)
    )
    assets = query.scalars().all()

    if not assets:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assets not found"
        )
    
    v_assets, _ = await validate_assets(session, assets)

    try:
        return v_assets
    except Exception as e:
        f_message = "An error occured while retrieving your assets."
        d_message = f"An error occured while retrieving agent {agent_id} asset. Reason {e}" 
        logger.error(d_message)
        log_message('error', d_message)
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = f_message
        )
    

async def get_unverified_properties(
    db: AsyncSession,
    page: int,
    size: int
) -> List[AssetResponseSchema]:
    """Returns unverified properties

    Args:
        db (AsyncSession): Postgress session
        page (int): pagination track
        size (int): pagination size

    Returns:
        _type_: a list of properties type
    """
    try:
        offset = (page-1) * size
        return (await db.execute(
            eager_asset_load()
            .where(
                and_(
                    Asset.verified == False,
                    Asset.datetime_declined.is_(None)   # exclude where datetime_declined is not null
                )
            )
            .offset(offset)
            .limit(size)
        )).scalars().all()
    except Exception as e:
        f_msg = "An error occured while retrieving your unverified properties."
        d_msg = f"{f_msg} Reason {e}" 
        if DEBUG:
            logger.error(d_msg)
        log_message('error', d_msg)
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = f_msg
        )
    

async def update_verification_state(
    asset_id: int,
    db: AsyncSession,
    action: Literal['verify','cancel'],
):
    """Mark an Asset as verified (verified=True).

    Args:
        asset_id: id of the Asset to verify
        db: AsyncSession
        action: verify or cancel

    Returns:
        The updated Asset instance
    """
    asset = await db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found.",
        )

    if action == 'verify':
        if asset.verified:
            # already verified — return as-is
            return asset

        asset.verified = True
    elif action == 'cancel':
        asset.verified = False
        asset.datetime_declined = datetime.now(timezone.utc)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action can be verify or cancel."
        )
    
    try:
        db.add(asset)
        await db.commit()
        await db.refresh(asset)
        if DEBUG:
            log_message('info', f"Asset {asset_id} marked as verified")
        return asset

    except Exception as e:
        await db.rollback()
        f_msg = f"Failed to {action} property."
        d_msg = f"{f_msg} Reason: {e}"
        if DEBUG:
            logger.error(d_msg)
        log_message('error', d_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f_msg,
        )