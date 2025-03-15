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
    id: Optional[int] = Field(None, description="Instance's id")
    phone_number: Optional[str] = Field(None, description="User's phone number")
    address: Optional[str] = Field(None, description="User's address")
    country: Optional[str] = Field(None, description="country")
    email_notification: Optional[bool] = Field(None, description="Email notification status")
    push_notification: Optional[bool] = Field(None, description="Push notification status")

    model_config = ConfigDict(from_attributes=True)
    

class UserFieldsForSettings(BaseModel):
    id: int = Field(..., description="user id")
    email: str = Field(..., description="user email")
    first_name: str = Field(..., description="User's firstname")
    last_name: Optional[str] = Field(None, description="User's lastname")
    has_settings: bool = Field(..., description="bool to indicate if the user has had a setting instance.")

    model_config = ConfigDict(from_attributes=True)


class SettingsSchema(UserFieldsForSettings):
    settings_data: UserSettingSchema