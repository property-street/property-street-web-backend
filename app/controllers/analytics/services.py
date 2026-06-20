from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession

from .enums import ResourceType
from .models import PlatformMetric

async def get_or_create_analytic_instance(db: AsyncSession, resource_type: ResourceType) -> PlatformMetric:
    metric_instance = await db.get(PlatformMetric, resource_type)
    if not metric_instance:
        metric_instance = PlatformMetric(resource_type=resource_type)
        db.add(metric_instance)
        await db.commit()
        await db.refresh(metric_instance)
    return metric_instance

async def update_metric_counters(
    db: AsyncSession,
    resource_type: ResourceType,
    **counters,
) -> PlatformMetric:
    if not counters:
        raise ValueError("At least one metric field must be provided")

    metric_instance = await get_or_create_analytic_instance(db, resource_type)
    for field, increment in counters.items():
        if field not in {
            'created_today',
            'created_this_week',
            'created_this_month',
            'total',
            'reported',
            'deleted',
            'active',
            'inactive',
            'suspended',
        }:
            raise ValueError(f"Unsupported metric field: {field}")
        current_value = getattr(metric_instance, field, 0) or 0
        setattr(metric_instance, field, current_value + int(increment))

    db.add(metric_instance)
    await db.commit()
    await db.refresh(metric_instance)
    return metric_instance


async def refresh_creation_counters(
    metric: PlatformMetric,
) -> None:
    today = date.today()

    # Daily
    if metric.last_day_reset != today:
        metric.created_today = 0
        metric.last_day_reset = today

    # Weekly
    current_week = today.isocalendar()[:2]  # (year, week)

    if (
        metric.last_week_reset is None
        or metric.last_week_reset.isocalendar()[:2] != current_week
    ):
        metric.created_this_week = 0
        metric.last_week_reset = today

    # Monthly
    current_month = (today.year, today.month)

    if (
        metric.last_month_reset is None
        or (
            metric.last_month_reset.year,
            metric.last_month_reset.month,
        ) != current_month
    ):
        metric.created_this_month = 0
        metric.last_month_reset = today


async def record_resource_creation(
    db: AsyncSession,
    resource_type: ResourceType,
    count: int = 1,
) -> PlatformMetric:
    # future JSON map
    # year
    #   month
    #       day
    return
    metric = await get_or_create_analytic_instance(
        db,
        resource_type,
    )

    await refresh_creation_counters(metric)
    
    return await update_metric_counters(
        db,
        resource_type,
        created_today=count,
        created_this_week=count,
        created_this_month=count,
        total=count,
    )


async def record_resource_deletion(
    db: AsyncSession,
    resource_type: ResourceType,
    count: int = 1,
) -> PlatformMetric:
    return
    return await update_metric_counters(db, resource_type, deleted=count)


async def record_resource_reported(
    db: AsyncSession,
    resource_type: ResourceType,
    count: int = 1,
) -> PlatformMetric:
    return await update_metric_counters(db, resource_type, reported=count)