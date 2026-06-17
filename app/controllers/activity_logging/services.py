import json
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from property_street_backend.app.controllers.actors.models import User
from property_street_backend.app.controllers.activity_logging.enums import ActivityStatusChoice
from property_street_backend.app.controllers.activity_logging.models import ActivityLog, EventLog
from property_street_backend.app.controllers.activity_logging.schemas import ActivityStatisticsSchema


async def log_activity(
    db: AsyncSession,
    user: User,
    action: str,
    status: ActivityStatusChoice = ActivityStatusChoice.pending,
    method: Optional[str] = None,
    endpoint: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request_body: Optional[str] = None,
    response_status_code: Optional[int] = None,
    response_time_ms: Optional[int] = None,
    description: Optional[str] = None,
) -> ActivityLog:
    activity = ActivityLog(
        user_id=user.id,
        action=action,
        status=status,
        description=description,
        method=method,
        endpoint=endpoint,
        ip_address=ip_address,
        user_agent=user_agent,
        request_body=request_body,
        response_status_code=response_status_code,
        response_time_ms=response_time_ms,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(activity)
    await db.commit()
    return activity


async def log_event(
    db: AsyncSession,
    user: User,
    event_type: str,
    action: str,
    status: ActivityStatusChoice = ActivityStatusChoice.success,
    affected_model: Optional[str] = None,
    affected_model_id: Optional[int] = None,
    affected_model_ids: Optional[str] = None,
    description: Optional[str] = None,
    payload: Optional[Any] = None,
) -> EventLog:
    if payload is not None and not isinstance(payload, str):
        payload = json.dumps(payload, default=str)

    event = EventLog(
        user_id=user.id,
        event_type=event_type,
        action=action,
        status=status,
        description=description,
        affected_model=affected_model,
        affected_model_id=affected_model_id,
        affected_model_ids=affected_model_ids,
        payload=payload,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def get_user_activities(
    db: AsyncSession,
    user: User,
    limit: int = 50,
    offset: int = 0,
    status_filter: Optional[ActivityStatusChoice] = None,
    days: Optional[int] = None,
) -> tuple[List[ActivityLog], int]:
    query = select(ActivityLog).where(ActivityLog.user_id == user.id)
    count_query = select(func.count(ActivityLog.id)).where(ActivityLog.user_id == user.id)

    if status_filter:
        query = query.where(ActivityLog.status == status_filter)
        count_query = count_query.where(ActivityLog.status == status_filter)
    if days:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        query = query.where(ActivityLog.timestamp >= cutoff_date)
        count_query = count_query.where(ActivityLog.timestamp >= cutoff_date)

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(query.order_by(ActivityLog.timestamp.desc()).offset(offset).limit(limit))
    return result.scalars().all(), total


async def get_activity_statistics(
    db: AsyncSession,
    user: User,
    days: Optional[int] = None,
) -> ActivityStatisticsSchema:
    query = select(ActivityLog).where(ActivityLog.user_id == user.id)
    if days:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        query = query.where(ActivityLog.timestamp >= cutoff_date)

    activities = (await db.execute(query)).scalars().all()
    total = len(activities)
    successful = sum(1 for item in activities if item.status == ActivityStatusChoice.success)
    failed = sum(1 for item in activities if item.status == ActivityStatusChoice.failed)
    pending = sum(1 for item in activities if item.status == ActivityStatusChoice.pending)
    error = sum(1 for item in activities if item.status == ActivityStatusChoice.error)
    action_counts = {}
    for item in activities:
        action_counts[item.action] = action_counts.get(item.action, 0) + 1

    return ActivityStatisticsSchema(
        total_activities=total,
        successful=successful,
        failed=failed,
        pending=pending,
        error=error,
        most_common_action=max(action_counts, key=action_counts.get) if action_counts else None,
        success_rate=round((successful / total * 100) if total else 0, 2),
    )


async def update_activity_status(
    db: AsyncSession,
    activity_id: int,
    activity_status: ActivityStatusChoice,
    response_status_code: Optional[int] = None,
    response_time_ms: Optional[int] = None,
) -> ActivityLog:
    activity = (await db.execute(select(ActivityLog).where(ActivityLog.id == activity_id))).scalars().first()
    if not activity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity log not found")

    activity.status = activity_status
    if response_status_code is not None:
        activity.response_status_code = response_status_code
    if response_time_ms is not None:
        activity.response_time_ms = response_time_ms
    db.add(activity)
    await db.commit()
    return activity
