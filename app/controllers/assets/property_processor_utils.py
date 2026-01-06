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
    AssetFeatureResponseSchema,
    PropertyResponseSchema,
)
from .services import eager_asset_load
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
from property_street_backend.app.controllers.activity.asset_routine_methods import (
    create_or_update_newly_created_asset_cache
)

def property_create_persistence_ttl() -> int:
    """returns the cache persistence property depending on context

    Returns:
        int: time in seconds
    """
    (TEST_NEWLY_CREATED_ASSET_TTL 
        if env_is_test() else 
    NEWLY_CREATED_ASSET_TTL)

async def notify_admin_on_new_property(property: Asset):
    try:
        admin_email = REAL_TEST_EMAIL if DEBUG else ADMIN_EMAIL 

        if admin_email:
            template = read_email_from_html_template_name('new_property_notification_template')
            host = 'http://localhost:3000' if DEBUG else 'https://propertystreet.ng'
            property_view_link = f"{host}/properties/{property.title}/{property.id}"
            property_location = f"{property.area.street}, {property.area.city_or_town}" if property.area else ""
            html = substituted_string(
                template or "New property ${property_title}",
                {
                    'agent_name': f'Agent {property.agent.username}',
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
                subject='New property created',
                to_email=admin_email,
                html_email=html,
            )
    except Exception as e:
        logger.error(f"Failed to send new property notification: {e}")


async def check_limit_exceeded(
    agent: User,
    db: AsyncSession,
):
    property_count = (await db.execute(
        select(func.count(Asset.id)).where(Asset.agent_id == agent.id)
    )).scalar_one()
    logger.info(f"***Property count: {property_count}")
    if property_count >= BETA_LAUNCH_PROPERTY_LIMIT:
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
        payload = data.model_dump(exclude_none=True)
        # logger.info(f"**Payload: {payload}")
        result = await apply_model(Asset, db, payload, instance=property)
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
    # logger.info(f"**Validated Features: {[AssetFeatureResponseSchema.model_validate(feature) for feature in property.features]}")
    # ===============
    # Handle caching
    # ===============
    try:
        schematized_asset = PropertyResponseSchema.model_validate(property) 
        schematized_asset_to_dict = schematized_asset.model_dump()
        await create_or_update_newly_created_asset_cache(
            asset_id = property.id,
            asset_data = schematized_asset_to_dict,
            redis_client = redis_client,
            newly_created = True,
            expiry_seconds = ttl_in_seconds,
        )
        if newly_created:
            await notify_admin_on_new_property(property)
    except Exception as e:
        logger.warning(f"Cache update failed: {e}")
        raise

    # ========================
    # Handle loggging
    # ========================
            
    return property