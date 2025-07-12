from datetime import date
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


from property_street_backend.app.models import UserSetting, User, Area
from property_street_backend.app.schemas.area_schema import AreaSchema

class UserSettingSchema(BaseModel):
    id: Optional[int] = Field(None, description="Instance's id")
    phone_number: Optional[str] = Field(None, description="User's phone number")
    email_notification: Optional[bool] = Field(None, description="Email notification status")
    push_notification: Optional[bool] = Field(None, description="Push notification status")
    areas: Optional[List[AreaSchema]] = Field(None, description="List of user's address areas")
    date_of_birth: Optional[date] = Field(None, description="User's date of birth")

    model_config = ConfigDict(from_attributes=True)
    

class UserSettingResponseSchema(BaseModel):
    id: Optional[int] = Field(None, description="Instance's id")
    email: str = Field(..., description="User's email address")
    first_name: str = Field(..., description="User's first name")
    last_name: Optional[str] = Field(..., description="User's last name")  
    has_settings: bool = Field(None, description="Indicates if the user has settings associated with them")
    phone_number: Optional[str] = Field(None, description="User's phone number")
    areas: Optional[List[AreaSchema]] = Field(None, description="list User's address")
    date_of_birth: Optional[date] = Field(None, description="User's date of birth")
    email_notification: Optional[bool] = Field(None, description="Email notification status")
    push_notification: Optional[bool] = Field(None, description="Push notification status")
    profile_avatar_url: Optional[str] = Field(None, description="User's profile avatar URL")

    model_config = ConfigDict(from_attributes=True)
    
    @classmethod
    def from_orm_with_relations(cls, user: User):
        settings: UserSetting = user.settings if hasattr(user, 'settings') else None
        areas: List[Area] = (
            [area for area in settings.areas]
            if settings and hasattr(settings, 'areas')
            else []
        )
        
        return cls(
            id=settings.id if settings else None,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            has_settings=True if settings else False,
            date_of_birth=(
                settings.date_of_birth 
                if settings and hasattr(settings, 'date_of_birth') 
                else None
            ),
            phone_number=(
                settings.phone_number 
                if settings and hasattr(settings, 'phone_number')
                else None
            ),
            areas=areas,
            email_notification=(
                settings.email_notification 
                if settings and hasattr(settings, 'email_notification')
                else False
            ),
            push_notification=(
                settings.push_notification 
                if settings and hasattr(settings, 'push_notification')
                else False
            ),
            profile_avatar_url=(
                user.profile_avatar.secure_url 
                if hasattr(user, 'profile_avatar') and user.profile_avatar 
                else None
            )
        )