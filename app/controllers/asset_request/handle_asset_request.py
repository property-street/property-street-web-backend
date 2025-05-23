import json
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.initiator import logger
from property_street_backend.config.settings import DEBUG
from property_street_backend.app.models import AssetRequest, Area
from property_street_backend.log_config.logger_config import log_message
from property_street_backend.app.controllers.ws_init import agent_specific_channels

async def handle_asset_request(
    requester_id: int,
    db: AsyncSession,
    request_data: dict,
    redis_client: Redis,
):
    """Saves the user's request to the database and publishes to the notification agent-wide

    Args:
        requester_id (int): request user id
        request_data (dict): object holding asset's description
        redis_client (Redis): Redis session object
        db (AsyncSession): postgres session object
    """
    try:
        # get the description and area entry
        # create and save an instance of the AssetRequest 
        description = request_data.get('description')
        area_collection = request_data.get('area')
        
        request_instance = AssetRequest(
            area = Area(**area_collection),
            description = description,
            requester_id = requester_id
        )
        db.add(request_instance)
        await db.commit()

        # publish the request to the asset_request channel
        await db.refresh(request_instance)
        request_data['db_id'] = request_instance.id,
        data_to_publish = {
            'request_data': request_data,
            'category': 'asset_request'
        }
        channel = agent_specific_channels['asset_request']
        await redis_client.publish(channel, json.dumps(data_to_publish))
        if DEBUG:
            log_message('success', f'Asset successfully requested!')
    except Exception as e:
        await db.rollback()
        log_message('error',f'An error occured while requesting asset. Reason: {e}')
        if DEBUG:
            logger.error("Asset creation error: %s",e)
        raise