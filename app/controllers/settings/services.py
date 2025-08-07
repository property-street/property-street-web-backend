import traceback
from typing import Dict
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession


from .schemas import UserSettingResponseSchema
from property_street_backend.app.controllers.utils import (
    create_or_update_object,
    return_model_from_string,
)
from property_street_backend.log_config.logger_config import (
    log_message
)
from property_street_backend.app.initiator import logger
from property_street_backend.config.settings import DEBUG
from property_street_backend.app.models import UserSetting, User
from property_street_backend.app.controllers.auth.services import get_password_hash


async def user_record_update(
    data_to_be_processed: Dict, 
    db: AsyncSession,
    user: User
):
    """
    Updates a user and the user_settings records.
    
    Args:
        data_to_be_processed (Dict): The data containing the objects to process.
        db (Session): The database session (injected by FastAPI).
    
    Returns:
        Dict: The result of the processing.
    """

    # Convert keys to integers for predictable ordering
    try:
        data = {int(k): v for k, v in data_to_be_processed.items()}
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid keys in data_to_be_processed. Keys must be integers."
        )

    try:
        # Initialize proxy object
        proxy = {}
        # Process the data
        for key, value in data.items():
            fields = value['fields']
            model_str = value['db_table_name']
            db_table_id = value['db_table_id']
            table_id = None if db_table_id == -1 else db_table_id

            if model_str == 'UserSetting':
                fields['user_id'] = user.id
                
            # Handle password hashing if updating User model
            if model_str == "User" :
                table_id = user.id

                if 'password' in fields:
                    fields['password_hash'] = get_password_hash(fields['password'])

            if DEBUG:
                logger.info(f"fields: {fields}")
            # Create or update object
            instance = await create_or_update_object(
                db = db,
                model = return_model_from_string(value['db_table_name']),
                fields = fields,
                proxyObject = proxy,
                table_id = table_id
            )
            proxy[key] = instance

        # Commit all changes after all operations are completed
        await db.commit()

        query = await db.execute(
            select(User)
            .options(
                selectinload(User.settings).selectinload(UserSetting.areas),
                selectinload(User.profile_avatar)
            )
            .where(User.id == user.id)
        )   
        result = query.scalars().one()

        if not result:
            raise HTTPException(status = status.HTTP_500_INTERNAL_SERVER_ERROR)

        # log a success message
        if DEBUG:
            logger.info(
                f'User records successfully updated'
            )
        
        return UserSettingResponseSchema.from_orm_with_relations(result)

    except Exception as e:
        await db.rollback()  # Rollback if there's an error to ensure atomicity
        f_message = "An error occured while updating user record"
        d_message=f'{f_message}: {traceback.format_exc()}'
        
        log_message(
            log_type='error',
            message = d_message
        )
        if DEBUG:
            logger.error(d_message)
        raise HTTPException(    
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f_message
        )
