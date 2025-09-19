from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from .models import RoommateFinder, RoomieApplication
from property_street_backend.app.initiator import logger
from property_street_backend.app.controllers.actors.models import User

def get_cached_roomies_application_ids(requester: User)->list:
    return requester.cached_roomies_application_ids

async def roommates_finder_request_application(applicant: User, request_id: int, session: AsyncSession):
    request = await session.get(RoommateFinder, request_id)
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Roommate finder request not found"
        )

    try:
        # create appplication
        session.add(RoomieApplication(
            applicant_id = applicant.id,
            roommate_finder_id = request_id
        ))
        await session.commit()

        # refresh and return applicant's updated cached_roomies_application ids
        await session.refresh(applicant)
        # notify the requester in a background task

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
        