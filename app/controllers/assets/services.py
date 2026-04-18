import json
import re
import unicodedata
from fastapi import status
from decimal import Decimal, InvalidOperation
from sqlalchemy import and_, or_
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
from .model_utils import (
    UserStatsPerProperty,
)
from .schemas import (
    StreamPayload,
    UserPropertyStats,
    InteractionEvents,
    NormalizedInteraction,
    PropertyResponseSchema,
    PartialPropertyResponseSchema,
)
from .enums import InteractionType
from .utils import eager_asset_load
from .stream import load_stream_state
from . import property_create_persistence_ttl
from property_street_backend.app.models import (
    User,
    Asset, 
    Area,
    Tag,
)
from property_street_backend.app.controllers.assets.models import AssetFeature
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
from .asset_routine_methods import add_asset_id_to_newly_created_cache
from property_street_backend.log_config.logger_config import log_message
from property_street_backend.app.controllers.assets.asset_routine_methods import (
    get_newly_created_asset_ids
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
    redis_client: Redis,
    user: Optional[User] = None,
):
    offset = (page - 1) * size
    results = []
    cache_ids = set()

    # === Step 1: Get asset IDs from Redis Cache ===
    cached_asset_ids = await get_newly_created_asset_ids(
        redis_client=redis_client,
        offset=offset,
        limit=size
    )

    cache_result_length = len(cached_asset_ids)
    
    # Query database for cached asset IDs
    if cached_asset_ids:
        result = await session.execute(
            eager_asset_load()
            .where(Asset.id.in_(cached_asset_ids))
            .order_by(Asset.id.in_(cached_asset_ids))  # Maintain cache order
        )
        cached_assets = result.scalars().all()
        results.extend(cached_assets)
        cache_ids = set(cached_asset_ids)

    remaining_size = size - cache_result_length

    # === Step 2: Fill remaining slots from DB ===
    if remaining_size > 0:
        db_offset = offset if not cache_ids else 0
        stmt = (
            eager_asset_load()
            .order_by(Asset.created_at.desc())
            .offset(db_offset)
            .limit(remaining_size)
        )

        # Skip already retrieved IDs
        if cache_ids:
            stmt = stmt.where(~Asset.id.in_(cache_ids))

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

    assets_with_stats = await enrich_property_engagement_data(valid_assets, session, user)
    return assets_with_stats


def normalize_search_text(value: Optional[str]) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text).strip().lower()


def split_csv_or_space(value: Optional[str]) -> list[str]:
    if not value:
        return []
    normalized = normalize_search_text(value.replace(",", " "))
    return [token for token in normalized.split(" ") if token]


def parse_seen_ids(seen_ids: Optional[list[int] | str]) -> list[int]:
    if not seen_ids:
        return []
    if isinstance(seen_ids, list):
        return [int(entry) for entry in seen_ids]
    return [int(entry) for entry in re.findall(r"\d+", seen_ids)]


def parse_decimal_or_none(value: Optional[str | float | int]) -> Optional[Decimal]:
    if value in [None, ""]:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


async def discover_properties(
    session: AsyncSession,
    user: Optional[User] = None,
    *,
    page: int = 1,
    size: int = 20,
    query: Optional[str] = None,
    category: Optional[str] = None,
    area: Optional[str] = None,
    status: Optional[str] = None,
    min_price: Optional[str | float | int] = None,
    max_price: Optional[str | float | int] = None,
    tags: Optional[str] = None,
    features: Optional[str] = None,
    seen_ids: Optional[list[int] | str] = None,
):
    offset = max(0, (page - 1) * size)
    normalized_query = split_csv_or_space(query)
    normalized_area = split_csv_or_space(area)
    normalized_tags = split_csv_or_space(tags)
    normalized_features = split_csv_or_space(features)
    normalized_category = normalize_search_text(category)
    normalized_status = normalize_search_text(status)
    parsed_seen_ids = parse_seen_ids(seen_ids)

    stmt = (
        eager_asset_load()
        .join(Area, Asset.area_id == Area.id)
        .outerjoin(Asset.tags)
        .outerjoin(Asset.features)
        .where(Asset.verified.is_(True))
        .distinct()
        .offset(offset)
        .limit(size)
    )

    if parsed_seen_ids:
        stmt = stmt.where(~Asset.id.in_(parsed_seen_ids))

    if normalized_category:
        stmt = stmt.where(Asset.category.ilike(f"%{normalized_category}%"))

    if normalized_status:
        stmt = stmt.where(Asset.status.ilike(f"%{normalized_status}%"))

    minimum = parse_decimal_or_none(min_price)
    maximum = parse_decimal_or_none(max_price)
    if minimum is not None:
        stmt = stmt.where(Asset.price >= minimum)
    if maximum is not None:
        stmt = stmt.where(Asset.price <= maximum)

    if normalized_area:
        stmt = stmt.where(and_(*[
            or_(
                Area.country.ilike(f"%{token}%"),
                Area.state_or_province.ilike(f"%{token}%"),
                Area.city_or_town.ilike(f"%{token}%"),
                Area.street.ilike(f"%{token}%"),
                Area.building_name_or_suite.ilike(f"%{token}%"),
            )
            for token in normalized_area
        ]))

    if normalized_tags:
        stmt = stmt.where(and_(*[
            Asset.tags.any(Tag.name.ilike(f"%{token}%"))
            for token in normalized_tags
        ]))

    if normalized_features:
        stmt = stmt.where(and_(*[
            Asset.features.any(AssetFeature.title.ilike(f"%{token}%"))
            for token in normalized_features
        ]))

    if normalized_query:
        stmt = stmt.where(and_(*[
            or_(
                Asset.title.ilike(f"%{token}%"),
                Asset.description.ilike(f"%{token}%"),
                Asset.category.ilike(f"%{token}%"),
                Asset.status.ilike(f"%{token}%"),
                Asset.listing_type.ilike(f"%{token}%"),
                Area.country.ilike(f"%{token}%"),
                Area.state_or_province.ilike(f"%{token}%"),
                Area.city_or_town.ilike(f"%{token}%"),
                Area.street.ilike(f"%{token}%"),
                Asset.tags.any(Tag.name.ilike(f"%{token}%")),
                Asset.features.any(AssetFeature.title.ilike(f"%{token}%")),
            )
            for token in normalized_query
        ]))

    result = await session.execute(stmt.order_by(Asset.created_at.desc()))
    assets = result.scalars().all()
    valid_assets, _ = await validate_assets(session, assets, verified_only=True)
    return await enrich_property_engagement_data(valid_assets, session, user)


async def enrich_property_engagement_data(
    assets: List[Asset],
    db: AsyncSession,
    user: Optional[User] = None,
):
    if not assets:
        return assets

    asset_ids = [asset.id for asset in assets if asset.id is not None]

    # Normalize underlying asset counters to non-null values
    for asset in assets:
        asset.total_ratings = asset.total_ratings or 0
        asset.total_stars = asset.total_stars or 0
        asset.likes = asset.likes or 0

    user_stats_by_asset_id: Dict[int, UserStatsPerProperty] = {}
    logger.info(f"**User: {user}")

    if user and asset_ids:
        result = await db.execute(
            select(UserStatsPerProperty).where(
                and_(
                    UserStatsPerProperty.user_id == user.id,
                    UserStatsPerProperty.asset_id.in_(asset_ids),
                )
            )
        )
        user_stats_by_asset_id = {
            stat.asset_id: stat
            for stat in result.scalars().all()
        }

    for asset in assets:
        stats = user_stats_by_asset_id.get(asset.id)
        # if DEBUG:
        #    logger.info(f"**User stats for {asset.id} {UserPropertyStats.model_validate(stats).model_dump()}") 
        asset.user_stats = UserPropertyStats(
            liked = bool(stats.liked) if stats else False,
            saved = bool(stats.saved) if stats else False,
            share_count = (stats.share_count or 0) if stats else 0,
            view_count = (stats.view_count or 0) if stats else 0,
        )

    return assets


async def fetch_agent_assets(
    session: AsyncSession,
    size: int,
    page: int,
    agent_id: int,
    user: Optional[User] = None,
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

    assets_with_stats = await enrich_property_engagement_data(v_assets, session, user)

    try:
        return assets_with_stats
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


async def handle_stream(
    user: Optional[User],
    size: int,
    db: AsyncSession,
    redis_client: Redis,
    stream_payload: StreamPayload,
):
    """Build stream response.

    The stream is personalized when the user is authenticated by including
    the user's per-property stats (likes, saves, view counts, etc.) on each asset.

    Args:
        user: Optional current user.
        size: Size per stream.
        db: Database session.
        redis_client: Redis client.
        stream_payload: dictionary of 
         - seen_ids: IDs that should be excluded from the stream.
         - db_cursor: `created-at` of the last asset
         - auto_cat_cursor: Last float for the auto-category zset (deduping).

    Returns:
        Object including seen_ids, cursors, and assets with `user_stats` injected when a user is present.
    """

    stream_result = await load_stream_state(
        user,
        size,
        db,
        redis_client,
        stream_payload
    )
    assets = stream_result['data']

    # If a user is present, attach the user's per-property stats to each asset
    if user:
        asset_ids = [asset.id for asset in assets]
        if asset_ids:
            stmt = select(UserStatsPerProperty).where(
                UserStatsPerProperty.user_id == user.id,
                UserStatsPerProperty.asset_id.in_(asset_ids),
            )
            result = await db.execute(stmt)
            stats_rows = result.scalars().all()
            stats_map = {s.asset_id: s for s in stats_rows}

            for asset in assets:
                stats = stats_map.get(asset.id)
                if stats:
                    asset.user_stats = {
                        "liked": bool(stats.liked),
                        "save": bool(stats.saved),
                        "share_count": stats.share_count or 0,
                        "view_count": stats.view_count or 0,
                    }
                else:
                    asset.user_stats = {
                        "liked": False,
                        "save": False,
                        "share_count": 0,
                        "view_count": 0,
                    }

    return {
        **stream_result,
        "data": assets
    }


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
    
        singleton_types = {
            InteractionType.like,
            InteractionType.save,
            InteractionType.cart,
        }

        if DEBUG:
            stats_by_user = None

        # Keep the last event for singleton types per user per property to avoid duplicate count bump
        singleton_latest: Dict[tuple[int, InteractionType], list] = {}
        non_singleton_events: List[Dict] = []

        for interaction in normalized_interactions:
            property_id = interaction['id']
            event_type = interaction['type']
            event_data = interaction['data']

            if event_type in singleton_types:
                singleton_latest[(property_id, event_type)] = event_data[-1:] if event_data else []
            else:
                non_singleton_events.append(interaction)

        normalized_interactions = non_singleton_events[:]
        for (property_id, event_type), event_data in singleton_latest.items():
            if event_data:
                normalized_interactions.append({
                    'id': property_id,
                    'type': event_type,
                    'data': event_data,
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
                if DEBUG:
                    stats_by_user = user_stats
                db.add(user_stats)
            
            event_type = interaction['type']

            seen_event_keys = set()
            for interaction_data in interaction['data']:
                event_key = f"{property_id}:{event_type}:{interaction_data.timestamp_ms}:{interaction_data.action}"
                if event_key in seen_event_keys:
                    continue
                seen_event_keys.add(event_key)

                # Verify property existence
                asset = await db.get(Asset, property_id)
                
                if not asset and DEBUG:
                    logger.warning(f"Property with ID {property_id} not found, skipping")
                    continue

                action = interaction_data.action
                
                # Create PropertyInteractionEvent
                interaction_event = PropertyInteractionEvent(
                    property_id=property_id,
                    timestamp_ms=interaction_data.timestamp_ms,
                    factor=event_type,
                    user_id=user_id
                )
                db.add(interaction_event)
                
                # Update user stats and asset stat based on action type
                match event_type:
                    case InteractionType.like:
                        prev_liked = user_stats.liked
                        new_liked = True if action else False
                        if prev_liked != new_liked:
                            delta = 1 if new_liked else -1
                            asset.likes = max(0, (asset.likes or 0) + delta)
                        user_stats.liked = new_liked
                    case InteractionType.save:
                        prev_saved = user_stats.saved
                        new_saved = True if action else False
                        if prev_saved != new_saved:
                            delta = 1 if new_saved else -1
                            asset.saves = max(0, (asset.saves or 0) + delta)
                        user_stats.saved = new_saved
                    case InteractionType.cart:
                        prev_cart = user_stats.cart
                        new_cart = True if action else False
                        if prev_cart != new_cart:
                            delta = 1 if new_cart else -1
                            asset.carts = max(0, (asset.carts or 0) + delta)
                        user_stats.cart = new_cart
                    case InteractionType.share:
                        user_stats.share_count = (user_stats.share_count or 0) + 1
                        asset.shares = ( asset.shares or 0) + 1
                    case InteractionType.view:
                        # check that the user-id is not the asset's agent-id
                        if user.id != asset.agent_id:
                            user_stats.view_count = (user_stats.view_count or 0) + 1
                            asset.views = (asset.views or 0) + 1
                    case InteractionType.click:
                        user_stats.click_count = (user_stats.click_count or 0) + 1
                        asset.clicks = (asset.clicks or 0) + 1
                    case InteractionType.contact:
                        user_stats.contact_count = (user_stats.contact_count or 0) + 1
                        asset.contacts = (asset.contacts or 0) + 1
                    case _:
                        raise ValueError(f"Unsupported interaction type: {event_type}")
                interaction_count += 1
            
        # Commit all changes
        await db.commit()

        if DEBUG:
            await db.refresh(stats_by_user)
            logger.info(f"**User stats {UserPropertyStats.model_validate(stats_by_user).model_dump()}")

        
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
