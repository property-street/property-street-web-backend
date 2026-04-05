import traceback
from sqlalchemy import func
from datetime import datetime
from redis.asyncio import Redis
from sqlalchemy.future import select
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession


from .schemas import (
    PropertySchema,
    PatchPropertySchema,
    PropertyResponseSchema,
)
from .services import eager_asset_load
from . import property_create_persistence_ttl
from .relationship_handler import apply_model
from property_street_backend.app.models import (
    User,
    Asset, 
)
from property_street_backend.config.settings import (
    DEBUG,
    ADMIN_EMAIL,
    BETA_LAUNCHING,
    REAL_TEST_EMAIL,
    NEWLY_CREATED_ASSET_TTL,
    BETA_LAUNCH_PROPERTY_LIMIT,
    UNLIMITED_BETA_AGENTS_EMAILS,
    TEST_NEWLY_CREATED_ASSET_TTL,
)
from property_street_backend.app.utils.store import (
    read_email_from_html_template_name,
    substituted_string,
    send_email,
)
from property_street_backend.config import env_is_test
from property_street_backend.app.initiator import logger
from property_street_backend.log_config.logger_config import (
    log_message
)
from property_street_backend.app.controllers.assets.asset_routine_methods import (
    add_asset_id_to_newly_created_cache
)


def notify_admin_on_new_property(property: Asset, new: bool = True):
    try:
        admin_email = REAL_TEST_EMAIL if DEBUG else ADMIN_EMAIL 

        if admin_email:
            template = read_email_from_html_template_name('new_property_notification_template')
            host = 'http://localhost:3000' if DEBUG else 'https://propertystreet.ng'
            property_view_link = f"{host}/properties/{property.title}/{property.id}"
            property_location = f"{property.area.street}, {property.area.city_or_town}" if property.area else ""
            html = substituted_string(
                template or ("New property ${property_title}" if new else "Updated property ${property_title}"),
                {
                    'title': 'New property created' if new else 'Updated property',
                    'message': 'A new property has been created' if new else 'A property has been updated',
                    'agent_name': f'Agent {property.agent.username.title()}',
                    'property_title': property.title,
                    'property_location': property_location,
                    'property_price': str(property.price),
                    'creation_date': datetime.now().isoformat(),
                    'property_view_link': property_view_link,
                    'property_street_address': 'Property street'
                }
            )
            # send email (do not block creation if this fails)
            send_email(
                from_email='support@propertystreet.ng',
                from_name='Property street',
                subject='New property created' if new else 'Property updated',
                to_email=admin_email,
                html_email=html,
            )
    except Exception as e:
        logger.error(f"Failed to send new or update property notification: {e}")


async def check_limit_exceeded(
    agent: User,
    db: AsyncSession,
):
    property_count = (await db.execute(
        select(func.count(Asset.id)).where(Asset.agent_id == agent.id)
    )).scalar_one()
    unlimited_beta_agents_emails = UNLIMITED_BETA_AGENTS_EMAILS
    if property_count >= BETA_LAUNCH_PROPERTY_LIMIT and agent.email not in unlimited_beta_agents_emails:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail = f"Property limit has reached for beta mode. 5 per agent."
        )


async def handle_property_create_update(
    data: PropertySchema|PatchPropertySchema, 
    db: AsyncSession,
    redis_client: Redis,
    agent: User,
    ttl_in_seconds: int = property_create_persistence_ttl(),
    newly_created: bool = True
):
    """Handles creation or update of properties

    Args:
        data (PropertySchema | PatchPropertySchema): Property schema
        db (AsyncSession): Database session
        redis_client (Redis): Cache session
        agent (User): Agent user
        ttl_in_seconds (int, optional): amount in time for the property to be cached as newly_created. Defaults to property_create_persistence_ttl().
        newly_created (bool, optional): Boolean to indicate creation status. Defaults to True.

    Raises:
        HTTPException: _description_

    Returns:
        _type_: _description_
    """
    if newly_created and BETA_LAUNCHING:
        await check_limit_exceeded(agent, db)
        
    property = await db.get(Asset,data.id) if getattr(data,'id') else None

    try:
        # Remove unaccounted None entries
        ALLOWED_NONE_FIELDS = {"lease_duration"}
        payload = {
            k: v
            for k, v in data.model_dump().items()
            if v is not None or k in ALLOWED_NONE_FIELDS
        }

        # logger.info(f"**Payload: {payload}")

        # Preparation of extra before commit function
        extra_before_commit = None
        if not newly_created:
            def extra(instance: Asset):
                instance.datetime_declined = None
                instance.verified = False
            extra_before_commit = extra 

        # Application of data
        result: Asset = await apply_model(
            Asset, db, payload, instance=property,
            extra_before_commit=extra_before_commit
        )
        property = (await db.execute(
            eager_asset_load()
            .where(Asset.id == result.id)
        )).scalars().first()
    except Exception as e:
        await db.rollback()  # Rollback if there's an error to ensure atomicity
        f_message=f'An error occured on processing of property. Reason: {e}'
        d_message=f'An error occured on processing of property. Reason: {traceback.format_exc()}'
        if DEBUG:
            logger.error(d_message)
        log_message(
            log_type = 'error',
            message = f_message
        )
        raise HTTPException(    
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = "An error occurred while creating the property."
        )
    
    # ===============
    # Handle caching
    # ===============
    try:
        await add_asset_id_to_newly_created_cache(
            asset_id=property.id,
            redis_client=redis_client,
            expiry_seconds=ttl_in_seconds,
        )
    except Exception as e:
        if DEBUG:
            logger.warning(f"Cache update failed: {e}")
    
    # ========================
    # Handle notification
    # ========================
    notify_admin_on_new_property(property, newly_created)

            
    return property