import json
from sqlalchemy import select
from redis.asyncio import Redis
from pydantic import ValidationError
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession


from .models import AssetRequest
from .schemas import AssetRequestResponseSchema
from property_street_backend.app.initiator import logger
from property_street_backend.config.settings import DEBUG
from property_street_backend.app.controllers.actors.models import User
from property_street_backend.app.controllers.assets.models import Asset
from property_street_backend.log_config.logger_config import log_message
from property_street_backend.app.controllers.assets.schemas import PropertySchema
from property_street_backend.app.controllers.assets.property_processor_utils import handle_property_create_update



async def fetch_recent_asset_request(
    page: int,
    size: int,
    session: AsyncSession,
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
                # f_message = "An error occurred while retrieving latest Asset-requests."
                # d_message = f"AssetRequest ID {asset_request_id or 'unknown'} failed validation. Reason: {ve}"
                # log_message(log_type="error", message=d_message)
                # logger.error(d_message)
                # raise HTTPException(status_code=500, detail=f_message)

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
    return AssetRequestResponseSchema.from_orm_with_relations(property_request)