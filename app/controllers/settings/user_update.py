import traceback
from typing import Dict
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.controllers.utils import (
    create_or_update_object,
    return_model_from_string,
)
from property_street_backend.log_config.logger_config import (
    log_message
)
from property_street_backend.app.controllers.auth import get_password_hash


async def user_record_update(
    data_to_be_processed: Dict, 
    db: AsyncSession,
):
    """
    Updates a user and the user_settings records.
    
    Args:
        data_to_be_processed (Dict): The data containing the objects to process.
        db (Session): The database session (injected by FastAPI).
    
    Returns:
        Dict: The result of the processing.
    """
    # Initialize proxy object
    proxy = {}

    # Convert keys to integers for predictable ordering
    try:
        data = {int(k): v for k, v in data_to_be_processed.items()}
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid keys in data_to_be_processed. Keys must be integers."
        )

    try:
        # Process the data
        for key, value in data.items():
            # Handle password hashing if updating User model
            if value['db_table_name'] == 'User' and 'password' in value['fields']:
                password = value['fields'].pop('password')
                value['fields']['password_hash'] = get_password_hash(password)

            # Create or update object
            instance = await create_or_update_object(
                db=db,
                model=return_model_from_string(value['db_table_name']),
                obj_data=value['fields'],
                proxyObject=proxy,
                table_id=None if value['db_table_id'] == -1 else value['db_table_id']
            )
            proxy[key] = instance

        # Commit all changes after all operations are completed
        await db.commit()
        
        return {
            "detail": "User record updated successfully",
            "status": "success", 
            "processed": len(data),
        }

    except Exception as e:
        await db.rollback()  # Rollback if there's an error to ensure atomicity
        log_message(
            log_type='error',
            message=f'Error updating user record: {traceback.format_exc()}'
        )
        raise HTTPException(    
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the user record."
        )
