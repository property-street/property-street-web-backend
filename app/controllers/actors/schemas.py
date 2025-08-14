from typing import Optional
from pydantic import Field, model_validator
from property_street_backend.app.schemas import ConfigDictSetter

from .models import User

class AgentResponseSchema(ConfigDictSetter):
    id: int
    username: str
    profile_avatar_url: Optional[str] = Field(None, description="Agent's avatar URL from the related user")

    @model_validator(mode='before')
    @classmethod
    def transform_agent_data(cls, data):
        if isinstance(data, User):  # Handle ORM object
            return {
                'id': data.id,
                'username': data.username,
                'profile_avatar_url': (
                    data.profile_avatar.secure_url 
                    if data and data.profile_avatar 
                    else ""
                )
            }
        return data  # Fallback for dict input
