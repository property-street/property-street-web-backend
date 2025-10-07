import json
import time
from sqlalchemy import select
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status, WebSocketException


from .models import RoommateFinder, RoomieApplication
from property_street_backend.app.initiator import logger
from property_street_backend.app.initiator import logger
from property_street_backend.config.settings import DEBUG
from property_street_backend.app.controllers.ws_init import (
    is_online,
    notification_ref, 
    channel_categories, 
    get_client_channel_key,
)
from property_street_backend.app.controllers.actors.models import User, SocialLog
from property_street_backend.app.controllers.notification.models import Notification
from property_street_backend.app.controllers.notification.schemas import NotificationResponse
from property_street_backend.app.controllers.notification.enums import NotificationTypeChoice
from property_street_backend.app.controllers.notification.utils import add_pending_notification_token_to_user_pool


async def roommates_finder_request_application(applicant: User, request_id: int, session: AsyncSession, redis_client: Redis):
    rf_request: RoommateFinder = await session.get(RoommateFinder, request_id)
    if not rf_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Roommate finder request not found"
        )
    requester_id = rf_request.requester_id
    applicant_id = applicant.id

    # ensure the applicant has not applied before
    query = await session.execute(
        select(RoomieApplication)
        .where(
            RoomieApplication.applicant_id == applicant_id,
            RoomieApplication.roommate_finder_id == rf_request.id
        )
    )
    application = query.scalars().first()
    if application:
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            detail="Duplicate application is disallowed"
        )

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
                user_id=applicant_id
            )
        )

        n_type = NotificationTypeChoice.roommate_finder.value
        notification_map = {
            'n_type': n_type,
            'timestamp': time.time(),
            'fmt_not': {
                'title': title,
                'media_urls': media_urls,
                'ref_model': notification_ref['roommates_finder'],
                'ref_id': rf_request.id
            },
        }
        # create notification for roommate requester
        notification = Notification(
            **notification_map,
            user_id=requester_id
        )
        session.add(notification)
        await session.flush()
        await session.refresh(notification)

        # commit all session additions
        await session.commit()
        if DEBUG:
            logger.info('**Roommate application changes committed')

        # notify the requester in a background task
        request_data = NotificationResponse.model_validate(notification).model_dump()
        data_to_publish = {
            'category': channel_categories['notification'],
            'data': request_data,
        }
        requester_channel = get_client_channel_key(requester_id)
        try:
            requester_is_online = await is_online(redis_client, requester_id)
            if not requester_is_online:
                raise WebSocketException(
                    code = status.WS_1008_POLICY_VIOLATION,
                )
            await redis_client.publish(requester_channel, json.dumps(data_to_publish))
        except Exception as e: # add the notification object to the client's pend_pool
            await add_pending_notification_token_to_user_pool(
                notification_id=notification.id,
                redis_client = redis_client,
                client_id = rf_request.requester_id
            )
            if DEBUG:
                logger.error(f'**Error publishing notification to requester channel. Reason: {e}')

        # refresh and return applicant's updated cached_roomies_application ids
        await session.refresh(applicant)

        return applicant.cached_roomies_application_ids
    except Exception as e:
        await session.rollback()
        f_message = f'Error while applying for a roommate finder request!'
        d_message=f'{f_message} Reason:{e}'
        if DEBUG:
            logger.error(d_message)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f_message
        )
        