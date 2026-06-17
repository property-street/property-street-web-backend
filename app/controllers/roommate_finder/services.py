from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import RoommateFinder
from pydantic import ValidationError
from .schemas import RoommateFinderResponseSchema
from property_street_backend.app.controllers.actors.models import User
from property_street_backend.app.controllers.activity_logging.services import log_event
from property_street_backend.log_config.logger_config import log_message
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

def get_cached_roomies_application_ids(requester: User)->list:
    return requester.cached_roomies_application_ids

def validate_rf_reqs(raw_requests):
    valid_requests = []
    skipped_requests = []
    
    for request in raw_requests:
        try:
            validated_asset = RoommateFinderResponseSchema.from_orm_with_relations(request)
            valid_requests.append(validated_asset)
        except ValidationError as ve:
            asset_id = getattr(request, 'id', request.get('id') if isinstance(request, dict) else None)
            skipped_requests.append(asset_id)
            log_message(
                log_type="error",
                message=f"RoomamteFinder ID {asset_id or 'unknown'} failed validation. Reason: {ve}"
            )
    return valid_requests, skipped_requests

async def handle_my_requests(
    page: int,
    size: int,
    db: AsyncSession,
    requester: User,
):
    offset = (page - 1) * size
    requests = (await db.execute(
        select(RoommateFinder)
        .where(RoommateFinder.requester_id == requester.id)
        .order_by(RoommateFinder.created_at.desc())
        .offset(offset)
        .limit(size)
    )).scalars().all()
    valid_reqs,_ = validate_rf_reqs(requests)
    return valid_reqs


async def delete_roommate_request(
    request_id: int,
    db: AsyncSession,
    requester: User,
):
    """Delete a RoommateFinder request. Allowed for the owner, staff or admin.

    Raises HTTPException on not found, forbidden or constraint errors.
    """
    # fetch the roommate request
    result = await db.execute(select(RoommateFinder).where(RoommateFinder.id == request_id))
    rf = result.scalars().first()
    if rf is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roommate request not found")

    # permission check: owner or staff/admin
    user_role = getattr(requester, 'user_role', None)
    is_privileged = user_role in ['staff', 'admin']
    if not (is_privileged or requester.id == rf.requester_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to delete this request")

    try:
        await db.delete(rf)
        await db.commit()

        try:
            await log_event(
                db=db,
                user=requester,
                event_type="roommate_finder",
                action="delete_roommate_request",
                affected_model="RoommateFinder",
                affected_model_id=request_id,
                description=f"Deleted roommate finder request {request_id}.",
                payload={"request_id": request_id},
            )
        except Exception as e:
            log_message('error', f"Failed to log roommate finder delete event {request_id}: {e}")

    except IntegrityError:
        # likely due to RESTRICT constraint (existing applications)
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete request with active applications")

    return {"detail": "deleted"}


async def get_roommate_request_by_id(request_id: int, db: AsyncSession):
    """Fetch a single RoommateFinder request by id, including related fields.

    Raises HTTPException 404 if not found.
    Returns a RoommateFinderResponseSchema instance.
    """
    result = await db.execute(
        select(RoommateFinder)
        .options(
            selectinload(RoommateFinder.area),
            selectinload(RoommateFinder.room_images),
            selectinload(RoommateFinder.requester),
        )
        .where(RoommateFinder.id == request_id)
    )
    rf = result.scalars().first()
    if rf is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roommate request not found")

    return RoommateFinderResponseSchema.from_orm_with_relations(rf)