import re
from redis.asyncio import Redis
from pydantic import ValidationError
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func, or_
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession


from .models import AssetRequest
from .schemas import AssetRequestResponseSchema
from property_street_backend.app.models import Area
from property_street_backend.app.initiator import logger
from property_street_backend.app.controllers.actors.models import User
from property_street_backend.app.controllers.assets.models import Asset
from property_street_backend.log_config.logger_config import log_message
from property_street_backend.app.controllers.analytics.enums import ResourceType
from property_street_backend.app.controllers.assets.schemas import PropertySchema
from property_street_backend.app.controllers.activity_logging.services import log_event
from property_street_backend.app.controllers.analytics.services import record_resource_reported
from property_street_backend.app.controllers.assets.property_processor_utils import handle_property_create_update



async def fetch_recent_asset_request(
    page: int,
    size: int,
    session: AsyncSession,
    user_id: int = None
):
    offset = (page - 1) * size

    stmt = (
        select(AssetRequest)
        .options(
            selectinload(AssetRequest.area),
            selectinload(AssetRequest.assets),
            selectinload(AssetRequest.requester)
            .selectinload(User.profile_avatar)
        )
        .order_by(AssetRequest.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    if user_id:
        stmt = stmt.where(
            AssetRequest.requester_id == user_id
        )

    result = await session.execute(stmt)
    raw_requests = result.scalars().all()

    valid_requests = []
    skipped_requests = []

    try:
        for request in raw_requests:
            try:
                validated_asset = AssetRequestResponseSchema.from_orm_with_relations(request)
                valid_requests.append(validated_asset)
            except ValidationError as ve:
                asset_request_id = getattr(request, 'id', None)
                skipped_requests.append(asset_request_id)
    except Exception as e:
        f_message = "An error occurred while retrieving latest Asset-requests."
        d_message = f"{f_message} Reason: {e}"
        log_message(log_type="error", message=d_message)
        logger.error(d_message)
        raise HTTPException(status_code=500, detail=f_message)

    logger.info(
        f"{len(valid_requests)} valid assets-requests returned. {len(skipped_requests)} skipped due to schema errors."
    )

    return valid_requests


async def fetch_self_requests(page: int, size: int, session: AsyncSession, user_id: int ):
    return await fetch_recent_asset_request(page, size, session, user_id)


def split_tokens(value: str) -> list[str]:
    if not value:
        return []
    normalized = re.sub(r"[,]", " ", value)
    tokens = [t.strip().lower() for t in normalized.split() if t.strip()]
    return tokens


def parse_seen_ids(seen_ids: str) -> list[int]:
    if not seen_ids:
        return []
    return [int(x) for x in re.findall(r"\d+", seen_ids)]


async def discover_asset_requests(
    session: AsyncSession,
    user: User | None = None,
    *,
    page: int = 1,
    size: int = 20,
    query: str | None = None,
    area: str | None = None,
    seen_ids: str | None = None,
):
    offset = (page - 1) * size

    tokens = split_tokens(query or "")
    area_tokens = split_tokens(area or "")
    parsed_seen = parse_seen_ids(seen_ids or "")

    base_stmt = (
        select(AssetRequest)
        .options(
            selectinload(AssetRequest.area),
            selectinload(AssetRequest.assets),
            selectinload(AssetRequest.requester)
            .selectinload(User.profile_avatar)
        )
        .order_by(AssetRequest.created_at.desc())
    )

    # apply filters to the base statement
    stmt = base_stmt

    if parsed_seen:
        stmt = stmt.where(~AssetRequest.id.in_(parsed_seen))

    if tokens:
        # match tokens in description or area fields
        for token in tokens:
            stmt = stmt.where(
                AssetRequest.description.ilike(f"%{token}%")
            )

    if area_tokens:
        for token in area_tokens:
            stmt = stmt.where(
                or_(
                    Area.country.ilike(f"%{token}%"),
                    Area.state_or_province.ilike(f"%{token}%"),
                    Area.city_or_town.ilike(f"%{token}%"),
                    Area.street.ilike(f"%{token}%"),
                    Area.building_name_or_suite.ilike(f"%{token}%"),
                )
            )

    # compute total count for pagination
    try:
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await session.execute(count_stmt)
        total_count = int(count_result.scalar_one() or 0)
    except Exception:
        total_count = 0

    paged_stmt = stmt.offset(offset).limit(size + 1)
    result = await session.execute(paged_stmt)
    requests = result.scalars().all()
    has_more = len(requests) > size
    if has_more:
        requests = requests[:size]

    valid_requests = []
    skipped = []
    try:
        for req in requests:
            try:
                validated = AssetRequestResponseSchema.from_orm_with_relations(req)
                valid_requests.append(validated)
            except ValidationError:
                skipped.append(getattr(req, 'id', None))
    except Exception as e:
        logger.error(f"Error discovering asset requests: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while discovering asset requests.")

    return {
        "requests": valid_requests,
        "has_more": has_more,
        "total_count": total_count,
    }


async def handle_resolve_property_request(
    id: int,
    agent: User,
    redis_client: Redis,
    session: AsyncSession,
    property_id: int = None,
    data: PropertySchema = None,
):
    #=====================================================
    # Check that either of data or property_id is provided
    #=====================================================
    if not (data or property_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            details="Property data or property id must be provided."
        )
    
    property = None
    #=======================
    # Get property request
    #=======================
    property_request = await session.get(AssetRequest,id)
    if not property_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            details="Property request not found."
        )
    
    #==========================
    # Get property if existent
    #==========================
    if property_id: 
        property = await session.get(Asset, property_id)
        if not property:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                details="Property referenced not found."
            )
        if property.agent_id == agent.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                details="Unauthorized to reference proeprty."
            )

    #==========================
    # Create property
    #==========================
    if data: 
        property = await handle_property_create_update(data,session,redis_client,agent)
    
    if not property:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details="An error occured creating resolution."
        )
        
    property_request.assets.append(property)
    await session.commit()
    await session.refresh(property_request)

    try:
        affected_ids = f"AssetRequest:{property_request.id},Asset:{property.id}"
        await log_event(
            db=session,
            user=agent,
            event_type="asset_request",
            action="resolve_asset_request",
            affected_model="AssetRequest",
            affected_model_id=property_request.id,
            affected_model_ids=affected_ids,
            description=(
                f"Resolved asset request {property_request.id} with property {property.id}."
            ),
            payload={
                "asset_request_id": property_request.id,
                "property_id": property.id,
            },
        )
    except Exception as e:
        logger.error(f"Failed to log resolve event for asset request {property_request.id}: {e}")

    try:
        await record_resource_reported(db=session, resource_type=ResourceType.property_request)
    except Exception as e:
        logger.error(
            f"Failed to persist property request resolution metric for request {property_request.id}: {e}"
        )

    return AssetRequestResponseSchema.from_orm_with_relations(property_request)