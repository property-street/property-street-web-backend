from typing import Optional
from pydantic import Field, model_validator
from property_street_backend.app.schemas import ConfigDictSetter

class AgentResponseSchema(ConfigDictSetter):
    id: int
    first_name: Optional[str] = Field(None, description="Agent's first name from the related user")
    profile_avatar_url: Optional[str] = Field(None, description="Agent's avatar URL from the related user")

    @model_validator(mode="before")
    @classmethod
    def flatten_user_fields(cls, values):
        user: dict = values.get("user")
        if user:
            values["first_name"] = user.get("first_name")
            profile_avatar: dict = user.get("profile_avatar")
            if profile_avatar:
                values["profile_avatar_url"] = profile_avatar.get("secure_url")
        return values