from sqlalchemy import select 
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.initiator import logger
from property_street_backend.config.settings import DEBUG
from property_street_backend.app.models import Rating, Area, User
from property_street_backend.log_config.logger_config import log_message
from property_street_backend.app.controllers.utils import return_model_from_string


async def rate_asset(
    data: dict,
    db: AsyncSession,
):
    asset_to_rate = data.pop('asset_to_rate') # pop out the asset_to_rate field
    Model: Area|User = return_model_from_string(asset_to_rate)
    asset_id = data.get('agent_id') or data.get('area_id')
    
    not_found_exception = HTTPException(
        status_code = status.HTTP_404_NOT_FOUND,
        detail = f'{Model} to rate not found'
    )
    # raise not found error if the asset_id does not exist
    if not asset_id:
        if DEBUG:
            logger.error(f'**asset_id {asset_id} not provided', exc_info=1)
        raise not_found_exception
    
    # retrieve the asset and raise a 404 
    # if not found error if the asset is not found
    stmt = await db.execute(
        select(Model).where(Model.id == asset_id)
    )
    asset = stmt.scalars().first()
    if not asset:
        if DEBUG:
            logger.error(f'**{Model} with id {asset_id} not provided', exc_info=1)
        raise not_found_exception
    
    try:
        # create the rating instance
        inst = Rating(
            **data
        )
        db.add(inst)

        # update the asset rating attributes
        asset.total_ratings += 1
        asset.total_stars += data['score']
        db.add(asset)

        # commit the trx to the database
        await db.commit()

        if DEBUG:
            logger.info(f'**Successful rating-review of {Model} class')
    except Exception as e:
        await db.rollback()
        msg = f'**An error occured rating {Model} class. Reason: {e}' 
        if DEBUG:
            logger.error(msg, exc_info=1)
        log_message('error',msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = f'An error occured rating {Model} class.'
        )