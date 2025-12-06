import secrets
from redis.asyncio import Redis
from sqlalchemy.future import select
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession


from .models import User
from .utils import get_staff_validity_link
from property_street_backend.app.utils.store import (
    send_email,
    substituted_string,
    read_email_from_html_template_name,
)
from property_street_backend.app.initiator import logger
from property_street_backend.config.settings import DEBUG
from property_street_backend.app.models import CloudImageDetail
from property_street_backend.log_config.logger_config import log_error


def staff_invite_hset_key(user_id):
    return f'{user_id}:staff-invite'


async def send_staff_invite_link(
    user_id: str,
    db: AsyncSession,
    redis_client: Redis,
):
    cache_hset_key = staff_invite_hset_key(user_id)
    if await redis_client.exists(cache_hset_key):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sent invite not yet expired."
        )
    
    user = await db.get(User, user_id)
    email = user.email
    if user.user_role in ['staff', 'admin']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must not be staff or admin."
        )
    
    token = f"{secrets.token_urlsafe()}_{user_id}"
    validity_secs=get_staff_validity_link()

    # call the email function and send the email
    # extract the email content from the template
    email_template_content = read_email_from_html_template_name('staff_invite_template')
    property_street_address = "Port Harcourt"
    
    host = "http://localhost:3000" if DEBUG else "https://propertystreet.ng"
    invite_link = f"{host}/staff-invite?token={token}"
    email_string = substituted_string(
        email_template_content,
        {
            "recipient_name": user.username,
            "inviter_name": "Property street admin",
            "expiry_minutes": "60",
            "invite_link": invite_link,
            "property_street_address": property_street_address
        }
    )
    from_address="admin@propertystreet.ng"
    to_address=email
    subject="Staff Invite"
    from_name="Property street"
    #to_name="Customer"

    try:
        send_email(
            from_email=from_address,
            to_email=to_address,
            from_name=from_name,
            subject=subject,
            html_email=email_string
        )
        await redis_client.hset(cache_hset_key,'token',token)
        await redis_client.expire(cache_hset_key,validity_secs)
    except Exception as e:
        f_msg="An error occured sending invite link to user."
        d_msg=f"{f_msg} Reason:{e}"
        if DEBUG:
            logger.error(d_msg)
        log_error(d_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f_msg,
            headers={"X-Error": "Server error"},
        )


async def accept_staff_invite(
    token: str,
    db: AsyncSession,
    redis_client: Redis,
):
    """Validate a staff invite token and upgrade the invited user to 'staff'.

    Token format: <random>_<user_id> (the send function appends _{user_id}).
    The function checks Redis for a matching token under the key
    `{user_id}:staff-invite` and, if valid, updates the user's role.
    """
    if not token or "_" not in token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invite token.",
        )

    # Extract user_id (token may contain underscores, so split from the right)
    try:
        user_id = int(token.rsplit("_", 1)[1])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invite token format.",
        )

    cache_hset_key = staff_invite_hset_key(user_id)
    exists = await redis_client.exists(cache_hset_key)
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invite link is invalid or has expired.",
        )

    stored_token = await redis_client.hget(cache_hset_key, "token")
    if stored_token is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invite token not found (expired or invalid).",
        )
    if isinstance(stored_token, bytes):
        stored_token = stored_token.decode()

    if stored_token != token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invite token does not match.",
        )

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if user.user_role in ["staff", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already staff or admin.",
        )

    # perform the upgrade
    user.user_role = "staff"
    try:
        db.add(user)
        await db.commit()
        await db.refresh(user)

        # remove the invite cache (cleanup)
        await redis_client.delete(cache_hset_key)
        return user
    except Exception as e:
        # rollback and log
        await db.rollback()
        f_msg = "Failed to upgrade user to staff."
        d_msg = f"{f_msg} Reason: {e}"
        if DEBUG:
            logger.error(d_msg)
        log_error(d_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f_msg,
        )
    
async def handle_update_profile_avatar(db: AsyncSession, user: User, data: dict):
    user.profile_avatar = CloudImageDetail(
        **data
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user.profile_avatar