from pydantic import (
    Field, 
    BaseModel, 
    ConfigDict,
)
from typing import Optional


class OptionalBaseModel(BaseModel):
    """Automatically makes all fields optional in subclasses."""
    def __init_subclass__(cls, **kwargs):
        for field in cls.__annotations__:
            cls.__annotations__[field] = Optional[cls.__annotations__[field]]


class UserSettingSchema(OptionalBaseModel):
    id: int = Field(..., description="Instance's id")
    phone_number: str = Field(..., description="User's phone number")
    address: str = Field(..., description="User's address")
    country: str = Field(..., description="country")
    email_notification: bool = Field(..., description="Email notification status")
    push_notification: bool = Field(..., description="Push notification status")

    model_config = ConfigDict(from_attributes=True)
    

class UserFieldsForSettings(BaseModel):
    id: int = Field(..., description="user id")
    email: str = Field(..., description="user email")
    first_name: str = Field(..., description="User's firstname")
    last_name: str = Field(..., description="User's lastname")
    has_settings: bool = Field(..., description="bool to indicate if the user has had a setting instance.")

    model_config = ConfigDict(from_attributes=True)


class SettingsSchema(UserFieldsForSettings):
    settings_data: UserSettingSchema