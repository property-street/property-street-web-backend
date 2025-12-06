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
    Area
)
from property_street_backend.app.initiator import logger
from property_street_backend.config.settings import DEBUG
from property_street_backend.log_config.logger_config import log_message
from property_street_backend.app.controllers.activity import (
    auto_category_hset_key,
    newly_created_asset_set_key, 
)
from property_street_backend.app.utils.store import (
    send_email,
    read_email_from_html_template_name,
    substituted_string,
)

def eager_asset_load():
    return (
        select(Asset)
        .options(
            selectinload(Asset.features),
            selectinload(Asset.tags),
            selectinload(Asset.area),
            selectinload(Asset.unfeatured_images),
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
            if validated_asset.verified:
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
        properties = (await db.execute(
            eager_asset_load()
            .where(
                and_(
                    Asset.verified.isnot(True),
                    Asset.datetime_declined.is_(None)   # exclude where datetime_declined is not null
                )
            )
            .offset(offset)
            .limit(size)
        )).scalars().all()
    
        v_assets, _ = await validate_assets(db, properties)
        return v_assets
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


async def send_verification_state_email(
    property: Asset,
    action: Literal['verify','cancel'],
    **kwargs
):
    """Send email notification when property is verified.
    
    Args:
        asset: The verified Asset object with agent relationship loaded
    """
    if action not in ['verify','cancel']:
        detail=f"Verification state email got a wrong action: {action}"
        if DEBUG:
            logger.error(detail)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )
    
    agent: User = property.agent
    action_is_verify = action == 'verify'
    cancellation_reason = kwargs.get('cancellation_reason',None)

    try:
        if not agent or not agent.email:
            log_message('warning', f"Agent email not found for asset {property.id}")
            return
        
        # Load the email template
        template = "property_verification_template" if action_is_verify else "property_cancellation_template"
        template_content = read_email_from_html_template_name(template)
        if not template_content:
            log_message('error', f"Could not load {action} template for asset {property.id}")
            return
        
        # Build the variable map
        area: Area = property.area
        property_location = f"{area.city_or_town}, {area.state_or_province}" if area else "Unknown Location"
        property_price = f"{property.currency} {property.price}" if property.price else "Contact for Price"
        verification_date = property.datetime_verified.strftime("%B %d, %Y") if property.datetime_verified else datetime.now(timezone.utc).strftime("%B %d, %Y")
        property_view_link = f"https://app.propertystreet.com/property/{property.id}"
        property_street_address = "Port Harcourt, Nigeria"
        
                
        if action == 'verify':
            substitution_map = {
                "agent_name": agent.username,
                "property_title": property.title,
                "property_location": property_location,
                "property_price": property_price,
                "verification_date": verification_date,
                "property_view_link": property_view_link,
                "property_street_address": property_street_address
            }
        elif action == 'cancel':
            cancellation_date = property.datetime_declined.strftime("%B %d, %Y") if property.datetime_declined else datetime.now(timezone.utc).strftime("%B %d, %Y")
            host = "http://localhost:3000" if DEBUG else "https://www.propertystreet.ng"
            property_edit_link = f"{host}/update-property/{property.id}"
            substitution_map = {
                "agent_name": agent.username,
                "property_title": property.title,
                "cancellation_reason": cancellation_reason or 'Property violates eligibiltity criteria. Contact support for more clarity.',
                "cancellation_date": cancellation_date,
                "property_edit_link": property_edit_link,
                "property_street_address": property_street_address
            }
        
        # Substitute variables in template
        html_email = substituted_string(template_content, substitution_map)
        
        subject="Your Property Has Been Verified! 🎉" if action_is_verify else "Property Verification Status Update"
        # Send email
        send_email(
            from_email="team@propertystreet.ng",
            from_name="Property street",
            subject=subject,
            to_email=agent.email,
            html_email=html_email
        )
        
        if DEBUG:
            log_message('info', f"{action} email sent to {agent.email} for asset {property.id}")
        
    except Exception as e:
        # Log error but don't fail the verification process
        d_msg = f"Failed to send {action} email for asset {property.id}. Reason: {e}"
        if DEBUG:
            logger.error(d_msg)
        log_message('error', d_msg)

    
async def update_verification_state(
    asset_id: int,
    db: AsyncSession,
    action: Literal['verify','cancel'],
    cancellation_reason: str = None,
):
    """Mark an Asset as verified (verified=True) or cancelled (verified=False).

    Args:
        asset_id: id of the Asset to verify
        db: AsyncSession
        action: verify or cancel
        cancellation_reason: reason for cancellation (only used when action is 'cancel')

    Returns:
        The updated Asset instance
    """
    # Fetch asset with agent relationship loaded
    stmt = eager_asset_load().where(Asset.id == asset_id)
    result = await db.execute(stmt)
    asset = result.scalars().first()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found.",
        )

    now = datetime.now(timezone.utc)
    if action == 'verify':
        asset.verified = True
        asset.datetime_declined = None
        asset.datetime_verified = now
    elif action == 'cancel':
        asset.verified = False
        asset.datetime_declined = now
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
            log_message('info', f"Asset {asset_id} marked as {action}")
        
        # Send appropriate email notification
        await send_verification_state_email(asset, action, cancellation_reason=cancellation_reason)
        
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


async def handle_delete_property(db: AsyncSession, id: int, agent: User):
    property = await db.get(Asset, id)
    if agent.user_role == 'agent' and property.agent_id != agent.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not authorized to carry this operation"
        )
    await db.delete(property)
    await db.commit()