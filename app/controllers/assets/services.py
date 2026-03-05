import json
from fastapi import status
from sqlalchemy import and_
from redis.asyncio import Redis
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.future import select
from datetime import datetime, timezone
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Literal, Optional, Dict


from .models import (
    PropertyInteractionEvent,
)
from .utils import (
    UserStatsPerProperty,
)
from .schemas import (
    InteractionEvents,
    NormalizedInteraction,
    PropertyResponseSchema,
    PartialPropertyResponseSchema,
)
from .enums import InteractionType
from . import property_create_persistence_ttl
from property_street_backend.app.models import (
    User,
    Asset, 
    Area
)
from property_street_backend.app.initiator import logger
from property_street_backend.config.settings import DEBUG
from property_street_backend.app.utils.store import (
    send_email,
    substituted_string,
    read_email_from_html_template_name,
)
from property_street_backend.app.controllers.activity import (
    auto_category_hset_key,
    newly_created_asset_set_key, 
)
from property_street_backend.log_config.logger_config import log_message
from property_street_backend.app.controllers.activity.asset_routine_methods import (
    create_or_update_newly_created_asset_cache,
    remove_asset_from_newly_created_asset_cache
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
    verified_only: bool = True,
):
    valid_assets = []
    skipped_assets = []

    for asset in assets:
        try:
            validated_asset = PropertyResponseSchema.model_validate(asset)
            if verified_only and not validated_asset.verified:
                continue
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
                    PropertyResponseSchema.model_validate(refreshed_asset)
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
        property_list = list(newly_created_asset_cache_dict.values())
        property_list.reverse()

        # Get portion from cache
        cache_slice = property_list[offset : offset + size]
        results.extend(cache_slice)

        # Record their IDs to skip in DB fetch
        for property in cache_slice:
            if isinstance(property, dict):
                seen_ids.add(property.get("id"))
            else:
                seen_ids.add(getattr(property, "id", None))

    # logger.info(f"Results: {results}")
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
        return []
    
    v_assets, _ = await validate_assets(session, assets, verified_only=False)

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
    

async def handle_get_all_properties(
    db: AsyncSession,
    page: int,
    size: int,
    verified_only: bool = False,
    from_latest: bool = True,
) -> List[PartialPropertyResponseSchema]:
    """Returns all properties

    Args:
        db (AsyncSession): Postgress session
        page (int): pagination track
        size (int): pagination size

    Returns:
        _type_: a list of properties type
    """
    try:
        offset = (page-1) * size
        query = (
            eager_asset_load()
            .order_by(Asset.created_at.desc() if from_latest else Asset.created_at.asc())
            .offset(offset)
            .limit(size)
        )
        if verified_only:
            query = query.where(Asset.verified == verified_only)

        properties = (await db.execute(query)).scalars().all()
        return properties
    except Exception as e:
        f_msg = "An error occured while retrieving all properties."
        d_msg = f"{f_msg} Reason {e}" 
        if DEBUG:
            logger.error(d_msg)
        log_message('error', d_msg)
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = f_msg
        )


async def handle_get_all_verified_properties(
    db: AsyncSession,
    page: int,
    size: int
) -> List[PropertyResponseSchema]:
    """Returns all verified properties

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
            .offset(offset)
            .limit(size)
        )).scalars().all()
        v_assets, _ = await validate_assets(db, properties, verified_only=True)
        return v_assets
    except Exception as e:
        f_msg = "An error occured while retrieving verified properties."
        d_msg = f"{f_msg} Reason {e}" 
        if DEBUG:
            logger.error(d_msg)
        log_message('error', d_msg)
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = f_msg
        )
    

async def get_unverified_properties(
    db: AsyncSession,
    page: int,
    size: int
) -> List[PropertyResponseSchema]:
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
    
        v_assets, _ = await validate_assets(db, properties, verified_only=False)
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
    redis_client: Redis,
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
    property = result.scalars().first()
    
    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found.",
        )

    property_id = property.id
    now = datetime.now(timezone.utc)
    action_is_verify = action == 'verify'
    action_is_cancel = action == 'cancel'
    if action_is_verify:
        property.verified = True
        property.datetime_declined = None
        property.datetime_verified = now
    elif action_is_cancel:
        property.verified = False
        property.datetime_declined = now
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action can be verify or cancel."
        )
    
    try:
        db.add(property)
        await db.commit()
        await db.refresh(property)
        if DEBUG:
            log_message('info', f"Asset {asset_id} marked as {action}")
        
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
    
    # ===============
    # Handle caching
    # ===============
    try:
        if action_is_verify:
            ttl_in_seconds = property_create_persistence_ttl()
            dumped_property = PropertyResponseSchema.model_validate(
                property
            ).model_dump()
            await create_or_update_newly_created_asset_cache(
                asset_id = property.id,
                asset_data = dumped_property,
                redis_client = redis_client,
                newly_created = False,
                expiry_seconds = ttl_in_seconds,
            )
        elif action_is_cancel:
            await remove_asset_from_newly_created_asset_cache(
                property_id, redis_client
            )
    except Exception as e:
        logger.warning(f"Cache update failed: {e}")
        raise

    # Send appropriate email notification
    await send_verification_state_email(property, action, cancellation_reason=cancellation_reason)
    
    return property



async def handle_delete_property(db: AsyncSession, id: int, agent: User):
    property = await db.get(Asset, id)
    if agent.user_role == 'agent' and property.agent_id != agent.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not authorized to carry this operation"
        )
    await db.delete(property)
    await db.commit()


def category_candidates_stmt(
    category: str,
    cursor: Optional[str],
    seen_ids: List[int],
    limit: int = 10,
):
    stmt = (
        select(Asset)
        .where(
            Asset.category == category,
            Asset.verified.is_(True),
            Asset.id.notin_(seen_ids),
        )
        .order_by(Asset.created_at.desc())
        .limit(limit)
    )

    if cursor:
        stmt = stmt.where(Asset.created_at < cursor)

    return stmt


async def handle_stream():
    pass


async def handle_persist_property_interaction(
    data: InteractionEvents,
    user: User,
    db: AsyncSession
):
    """
    Persist user interactions with properties.
    
    Creates PropertyInteractionEvent records for each interaction and updates
    UserStatsPerProperty to track user engagement metrics (likes, saves, etc.)
    
    Args:
        data: List of PropertyInteraction objects containing property_id and interaction data
        user: Optional current user (can be anonymous)
        db: Database session
        
    Returns:
        Dict with success status and count of processed interactions
    """
    user_id = user.id
    interaction_count = 0
    user_stats_per_asset_map: Dict[int, UserStatsPerProperty] = {}
    normalized_interactions: List[NormalizedInteraction] = []
    try:
        for property_id, interactions in data.items():
            for type, data in interactions.items():
                normalized_interactions.append({
                    "id": property_id,
                    "type": type,
                    "data": data
                })
    
        for interaction in normalized_interactions:
            property_id = interaction['id']

            user_stats: UserStatsPerProperty = user_stats_per_asset_map.get(property_id)
            if not user_stats:
                stats_result = await db.execute(
                    select(UserStatsPerProperty).where(
                        and_(
                            UserStatsPerProperty.asset_id == property_id,
                            UserStatsPerProperty.user_id == user_id,
                        )
                    )
                )
                user_stats = stats_result.scalars().first()
                
                if not user_stats:
                    user_stats = UserStatsPerProperty(
                        asset_id=property_id,
                        user_id=user.id,
                        liked=False,
                        saved=False,
                        cart=False,
                        share_count=0,
                        view_count=0,
                        click_count=0,
                        contact_count=0
                    )
                user_stats_per_asset_map[property_id] = user_stats
                db.add(user_stats)
            
            event_type = interaction['type']

            for interaction_data in interaction['data']:
                # Verify property existence
                asset = await db.get(Asset, property_id)
                
                if not asset:
                    logger.warning(f"Property with ID {property_id} not found, skipping")
                    continue

                action = interaction_data.action
                timestamp = interaction_data.timestamp
                
                # Convert Unix timestamp to datetime
                event_timestamp = datetime.fromtimestamp(timestamp / 1000)  # Convert from milliseconds
                
                # Create PropertyInteractionEvent
                interaction_event = PropertyInteractionEvent(
                    property_id=property_id,
                    created_at=event_timestamp,
                    factor=event_type,
                    user_id=user_id
                )
                db.add(interaction_event)
                
                # Update user stats and asset stat based on action type
                match event_type:
                    case InteractionType.like:
                        user_stats.liked = True if action else False
                        asset.likes = max(0, asset.likes + (1 if action else -1))
                    case InteractionType.save:
                        user_stats.saved = True if action else False
                        asset.saves = max(0, asset.saves + (1 if action else -1))
                    case InteractionType.cart:
                        user_stats.cart = True if action else False
                        asset.carts = max(0, asset.carts + (1 if action else -1))
                    case InteractionType.share:
                        user_stats.share_count += 1
                        asset.shares += 1
                    case InteractionType.view:
                        # check that the user-id is not the asset's agent-id
                        if user.id != asset.agent_id:
                            user_stats.view_count += 1
                            asset.views += 1
                    case InteractionType.click:
                        user_stats.click_count += 1
                        asset.clicks += 1
                    case InteractionType.contact:
                        user_stats.contact_count += 1
                        asset.contacts += 1
                    case _:
                        raise ValueError(f"Unsupported interaction type: {event_type}")
                interaction_count += 1
            
        # Commit all changes
        await db.commit()
        
        logger.info(f"Successfully processed {interaction_count} interactions")
        
        return {
            "status": "success",
            "message": f"Processed {interaction_count} property interactions",
            "count": interaction_count,
        }
    
    except Exception as e:
        await db.rollback()
        logger.error(f"Error processing property interactions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process interactions: {str(e)}"
        )