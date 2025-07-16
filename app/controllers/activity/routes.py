import redis.asyncio as redis
from typing import Dict, Optional
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, status, HTTPException

from property_street_backend.app.models import (
    User,
    Asset,
)
from property_street_backend.app.database import get_db
from property_street_backend.app.controllers.auth.services import (
    decode_user_from_token,
    decode_user_from_token_optional,
)
from property_street_backend.app.initiator import get_redis
from property_street_backend.app.schemas.auth_schemas import (
    TokenData, 
)
from property_street_backend.log_config.logger_config import log_message
from property_street_backend.app.controllers.settings.services import user_record_update
from property_street_backend.app.controllers.activity.schemas import LatestCollectionSchema
from property_street_backend.app.schemas.route_based_asset_schemas import UserUIMetaDataSchema
from property_street_backend.app.controllers.activity.latest_collection import fetch_latest_collection


router = APIRouter(prefix="/activity", tags=["activity"])



@router.get("/user-ui-metadata",response_model=UserUIMetaDataSchema)
async def fetch_user_ui_metadata(
    current_user: Optional[TokenData] = Depends(decode_user_from_token_optional)
):
    """
    Fetches the user's ui metadata
    """
    try:
        # Determine user status
        is_authenticated = current_user is not None
        user_details = (
            {
                "first_name": current_user.first_name,
                "client_is_agent": True if current_user.agent_profile else False,
                "user_id": current_user.id,
                "profile_avatar_url": current_user.profile_avatar.secure_url if current_user.profile_avatar else None
            }
            if is_authenticated else {}
        )

        log_message(
            log_type="success",
            message="User ui metadata successfully retrieved"
        )

        # Return assets and user authentication status
        return {
            "is_authenticated": is_authenticated,
            **user_details,
        }

    except Exception as e:
        log_message(
            log_type="error",
            message=f"An error occurred on retrieval of user ui metadata. Reason: {e}"
        )
        raise HTTPException(status_code=500, detail=str(e))

    
@router.post("/update-profile-thumbnail", status_code=status.HTTP_200_OK)
async def user_profile_thumbnail_update(
    data: Dict, 
    db: AsyncSession = Depends(get_db),
    user: User = Depends(decode_user_from_token)
):
    return await user_record_update(
        data_to_be_processed = data,
        db = db,
        user = user
    )


@router.get("/latest-collection")
async def latest_collection(
    page: int = 1,
    size: int = 20,
    redis_client: redis.Redis = Depends(get_redis),
    session: AsyncSession = Depends(get_db),
):
    """
    Fetches the latest collection of assets, roommate finder requests, and asset requests.
    """
    return await fetch_latest_collection(
        page=page,
        size=size,
        session=session,
        redis_client=redis_client
    )