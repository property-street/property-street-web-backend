from fastapi import (
    Depends,
    APIRouter,
)


from property_street_backend.app.controllers.auth import (
    decode_user_from_token,
)
from property_street_backend.app.schemas.auth_schemas import (
    TokenData, 
)
from property_street_backend.app.schemas.settings_schemas import SettingsSchema

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
