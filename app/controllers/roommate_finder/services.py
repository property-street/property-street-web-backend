import json
from redis.asyncio import Redis
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from .models import RoommateFinder, RoomieApplication
from property_street_backend.app.initiator import logger
from property_street_backend.app.initiator import logger
from property_street_backend.app.controllers.actors.models import User, SocialLog
from property_street_backend.app.controllers.notification.models import Notification
from property_street_backend.app.controllers.notification.schemas import NotificationResponse
from property_street_backend.app.controllers.notification.enums import NotificationTypeChoice
from property_street_backend.app.controllers.notification.utils import add_pending_notification_token_to_user_pool
from property_street_backend.app.controllers.ws_init import channel_categories, notification_ref, get_client_channel_key

def get_cached_roomies_application_ids(requester: User)->list:
    return requester.cached_roomies_application_ids

async def roommates_finder_request_application(applicant: User, request_id: int, session: AsyncSession, redis_client: Redis):
    rf_request: RoommateFinder = await session.get(RoommateFinder, request_id)
    if not rf_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Roommate finder request not found"
        )
    requester_id = rf_request.requester_id

    try:
        # create appplication
        session.add(RoomieApplication(
            applicant_id = applicant.id,
            roommate_finder_id = request_id
        ))

        title='Roomie appliation'
        media_urls = [rf_request.room_images[0].secure_url]
        
        # save to applicant's activities
        session.add(
            SocialLog(
                title='Roomie appliation',
                media_urls=media_urls,
                user_id=applicant.id
            )
        )

        n_type = NotificationTypeChoice.roommate_finder.value
        n_data = {
            'n_type': n_type,
            'fmt_not': {
                'title': title,
                'media_urls': media_urls,
                'ref_model': notification_ref['roommates_finder'],
                'ref_id': rf_request.id
            },
        }
        # create notification for user
        notification = Notification(
            **n_data,
            user_id=requester_id
        )
        session.add(notification)
        await session.flush()
        await session.refresh(notification)

        # commit all session additions
        await session.commit()
        if DEBUG:
            logger.info('')

        # notify the requester in a background task
        request_data = NotificationResponse.model_validate(notification).model_dump()
        data_to_publish = {
            'category': channel_categories['notification'],
            'request_data': request_data,
        }
        requester_channel = get_client_channel_key(requester_id)
        try:
            await redis_client.publish(requester_channel, json.dumps(data_to_publish))
        except: # add the notification object to the client's pend_pool
            await add_pending_notification_token_to_user_pool(
                notification_id=notification.id,
                redis_client = redis_client,
                client_id = rf_request.requester_id
            )

        # refresh and return applicant's updated cached_roomies_application ids
        await session.refresh(applicant)

        return applicant.cached_roomies_application_ids
    except Exception as e:
        await session.rollback()
        f_message = f'Error while applying for a roommate finder request!'
        d_message=f'{f_message} Reason:{e}'
        logger.error(d_message)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f_message
        )
        