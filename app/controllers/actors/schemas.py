from typing import Optional
from pydantic import Field, model_validator
from property_street_backend.app.schemas import ConfigDictSetter

from .models import Agent

class AgentResponseSchema(ConfigDictSetter):
    id: int
    first_name: str
    profile_avatar_url: Optional[str] = Field(None, description="Agent's avatar URL from the related user")

    @model_validator(mode='before')
    @classmethod
    def transform_agent_data(cls, data):
        if isinstance(data, Agent):  # Handle ORM object
            return {
                'id': data.id,
                'first_name': data.user.first_name if data.user else "",
                'profile_avatar_url': (
                    data.user.profile_avatar.secure_url 
                    if data.user and data.user.profile_avatar 
                    else ""
                )
            }
        return data  # Fallback for dict input
