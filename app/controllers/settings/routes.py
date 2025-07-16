from fastapi import (
    Body,
    Depends,
    APIRouter,
)
from typing import Dict
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, status, HTTPException


from .schemas import UserSettingResponseSchema
from property_street_backend.app.database import get_db
from property_street_backend.config.settings import DEBUG
from property_street_backend.app.controllers.auth.services import (
    decode_user_from_token,
    get_password_hash,
    verify_password,
)
from property_street_backend.app.models import User, UserSetting
from property_street_backend.app.schemas.auth_schemas import TokenData 
from property_street_backend.log_config.logger_config import log_message
from property_street_backend.app.controllers.settings.services import user_record_update


router = APIRouter(prefix="/settings", tags=["settings"])


@router.get(
    "",
    response_model=UserSettingResponseSchema
)
async def fetch_user_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(decode_user_from_token),
):
    query = await db.execute(
        select(User)
        .options(
            selectinload(User.settings).selectinload(UserSetting.areas),
            selectinload(User.profile_avatar)
        )
        .where(User.id == current_user.id)
    )   
    result = query.scalars().one()
    
    return UserSettingResponseSchema.from_orm_with_relations(result)


@router.post("/update-user-and-settings", response_model = UserSettingResponseSchema, status_code=status.HTTP_200_OK)
async def update_user_and_settings(
    data: Dict, 
    db: AsyncSession = Depends(get_db),
    user: TokenData = Depends(decode_user_from_token)
):
    return await user_record_update(
        data_to_be_processed=data,
        db = db,
        user = user
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


