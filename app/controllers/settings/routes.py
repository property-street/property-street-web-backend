from fastapi import (
    Body,
    Depends,
    APIRouter,
)
from typing import Dict
from sqlalchemy import select
from redis.asyncio import Redis
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, status, HTTPException


from .utils import (
    get_password_update_ttl,
    password_update_set_token,
)
from .schemas import (
    EmailUpdateVerification,
    UserSettingResponseSchema,
    PasswordVerificationForUpdate,
)
from property_street_backend.app.database import get_db
from property_street_backend.config.settings import DEBUG
from property_street_backend.app.initiator import get_redis, logger
from property_street_backend.app.controllers.auth.services import (
    get_password_hash,
    verify_password,
    authenticate_user,
    decode_user_from_token,
    confirm_email_verification_code
)
from property_street_backend.app.models import User, UserSetting
from property_street_backend.app.schemas.auth_schemas import TokenData 
from property_street_backend.log_config.logger_config import log_message
from property_street_backend.log_config.logger_config import log_error 
from property_street_backend.app.controllers.settings.services import (
    user_record_update,
    email_uniqueness_check,
)
from property_street_backend.app.controllers.auth.services import confirm_email_verification_code 
from property_street_backend.app.controllers.auth.schemas import ConfirmEmailVerificationCodeSchema


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


@router.post("/delete-account", status_code=status.HTTP_200_OK)
async def delete_account(
    db: AsyncSession = Depends(get_db),
    user: TokenData = Depends(decode_user_from_token)
):
    await db.delete(user)
    await db.commit()


@router.post("/confirm-password-for-update", status_code=status.HTTP_200_OK)
async def confirm_password_for_update(
    data: PasswordVerificationForUpdate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(decode_user_from_token),
    redis_client: Redis = Depends(get_redis)
):
    email = current_user.email
    if not await authenticate_user(db,email,data.password):
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail="Password is wrong!"
        )
    key = password_update_set_token(email)
    await redis_client.set(key, 1, ex=get_password_update_ttl())


@router.post("/update-password", status_code=status.HTTP_200_OK)
async def update_password(
    data: PasswordVerificationForUpdate = Body(...),  # Ensures the request body is required
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
    current_user: User = Depends(decode_user_from_token),
):
    password_update_token = password_update_set_token(current_user.email)
    if not await redis_client.get(password_update_token):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Window for password update close. Try again"
        )
    
    new_password = data.password

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
    finally:
        await redis_client.delete(password_update_token)


@router.post("/email-update-validation", status_code=status.HTTP_200_OK)
async def check_email_update_validity(
    data: EmailUpdateVerification = Body(...),  # Ensures the request body is required
    db: AsyncSession = Depends(get_db),
    _: User = Depends(decode_user_from_token),
):
    return await email_uniqueness_check(db,data.email)


@router.post("/confirm-email-update", status_code=status.HTTP_200_OK)
async def email_update_confirmation(
    data: ConfirmEmailVerificationCodeSchema = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(decode_user_from_token),
    redis_client: Redis = Depends(get_redis),
):
    await confirm_email_verification_code(data.model_dump(),redis_client)
    email = data.email
    await email_uniqueness_check(db, email)
    try:
        current_user.email = email
        db.add(current_user)
        await db.commit()
    except Exception as e:
        await db.rollback()
        f_message = "An error occurred while updating email address."
        d_message = f"{f_message} Reason: {e}"
        if DEBUG:
            logger.info(d_message)
        log_error(d_message)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f_message
        )