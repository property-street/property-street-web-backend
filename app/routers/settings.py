from fastapi import (
    Body,
    Depends,
    APIRouter,
)
from typing import Dict
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession


from property_street_backend.app.database import get_db
from property_street_backend.app.controllers.auth import (
    decode_user_from_token,
    get_password_hash,
    verify_password,
)
from property_street_backend.config.settings import (
    DEBUG
)
from property_street_backend.log_config.logger_config import (
    log_message
)
from property_street_backend.app.schemas.auth_schemas import (
    TokenData, 
)
from property_street_backend.app.schemas.settings_schemas import SettingsSchema
from property_street_backend.app.controllers.settings.user_update import user_record_update


router = APIRouter(prefix="/settings", tags=["settings"])


@router.get(
    "",
    response_model=SettingsSchema
)
async def fetch_user_settings(
    current_user: TokenData = Depends(decode_user_from_token),
):
    setting_instance = current_user.user_settings
    
    user_data = {
        "id": current_user.id,
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "has_settings": True if setting_instance else False
    }

    setting_data = {
        "id": setting_instance.id if setting_instance else -1,
        "phone_number": setting_instance.phone_number if setting_instance else None,
        "address": setting_instance.address if setting_instance else None,
        "country": setting_instance.country if setting_instance else None,
        "email_notification": setting_instance.email_notification if setting_instance else False,
        "push_notification": setting_instance.push_notification if setting_instance else False,
    }
    
    return {
        **user_data, 
        "settings_data": setting_data
    }


@router.post("/update-user-and-settings", status_code=status.HTTP_200_OK)
async def update_user_and_settings(
    data: Dict, 
    db: AsyncSession = Depends(get_db),
    _: TokenData = Depends(decode_user_from_token)
):
    try:
        await user_record_update(
            data_to_be_processed=data,
            db = db,
        )
        # log a success message
        if DEBUG:
            log_message(
                log_type='success',
                message=f'user successfully updated'
            )
    except Exception as e:
        # log the error
        if DEBUG:
            log_message(
                log_type='error',
                message=f'An error occured while updating user record. Reason: {e}'
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occured on updating user record"
        )


@router.post("/update-password", status_code=status.HTTP_200_OK)
async def update_password(
    data: Dict = Body(...),  # Ensures the request body is required
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(decode_user_from_token)
):
    # ✅ Ensure 'password' is provided in the request body
    if "password" not in data or not data["password"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password field is required and cannot be empty"
        )

    new_password = data["password"]

    # ✅ Prevent updating to the same password
    if verify_password(new_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password cannot be the same as the current password!"
        )

    try:
        # ✅ Hash and update the password
        new_password_hash = get_password_hash(new_password)
        current_user.password_hash = new_password_hash
        db.add(current_user)
        await db.commit()

        # ✅ Log success
        if DEBUG:
            log_message(
                log_type="success",
                message="User password successfully updated"
            )

    except Exception as e:
        # ✅ Log and raise a 500 error if an exception occurs
        if DEBUG:
            log_message(
                log_type="error",
                message=f"An error occurred while updating password. Reason: {e}"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating password"
        )


