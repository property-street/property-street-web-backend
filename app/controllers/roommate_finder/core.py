import json
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from .models import RoommateFinder
from .schemas import RoommateFinderResponseSchema
from property_street_backend.app.initiator import logger
from property_street_backend.config.settings import DEBUG
from property_street_backend.log_config.logger_config import log_message
from property_street_backend.app.models import Area, CloudImageDetail, User
from property_street_backend.app.controllers.ws_init import generic_channels


async def publish_roommate_finding(
    request_data: dict,
    requester: User,
    db: AsyncSession,
    redis_client: Redis,
):
    try:
        requester_id = requester.id
        area = request_data.get('area')
        roommate_finder = RoommateFinder(
            area = Area(**area),
            requester_id = requester_id,
            max_roomies = request_data['max_roomies'],
            category = request_data['category'],
            extra_conditions = request_data.get('extra_conditions',''),
            room_images = [
                CloudImageDetail(
                    **room_cloud_images
                ) for room_cloud_images in request_data.get('room_images')
            ]
        )
        db.add(roommate_finder)

        # modify requester gender if unset
        if not requester.gender:
            requester.gender = request_data['gender']
            db.add(requester)

        await db.commit()

        await db.refresh(roommate_finder)
        response = RoommateFinderResponseSchema.from_orm_with_relations(roommate_finder)
        
        channel_payload = response.model_dump(exclude_none=True)
        # add the id of the roommate finder instance to the request_data
        channel_payload['db_id'] = roommate_finder.id,

        
        channel_category = 'roommates_finder'
        data_to_publish ={
            'request_data': channel_payload,
            'category': channel_category
        }
        channel = generic_channels.get(channel_category)
        await redis_client.publish(channel, json.dumps(data_to_publish))

        if DEBUG:
            logger.info('**Roommate finder request successfully published.')
        
        return response
    except Exception as e:
        await db.rollback()
        msg = f'**An error occured while requesting for a roommate finder. reason:{e}'
        if DEBUG:
            logger.info(msg)
        log_message('error',msg)