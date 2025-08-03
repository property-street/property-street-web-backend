from datetime import datetime
from typing import Optional, Any
from pydantic import field_validator

from property_street_backend.app.models import User, CloudImageDetail
from property_street_backend.app.schemas import ConfigDictSetter

class CloudImageSchema(ConfigDictSetter):
    secure_url: str


class UserMiniSchema(ConfigDictSetter):
    id: int
    first_name: str
    profile_avatar: Optional[dict] = None
    
    @field_validator('profile_avatar', mode='before')
    def transform_field_validator(cls, value):
        if isinstance(value, CloudImageDetail) and hasattr(value, 'secure_url'):
            return {'url': value.secure_url}
        return None


class MessageSummarySchema(ConfigDictSetter):
    id: int
    fmt_msg: Any
    server_timestamp_ms: int
    status: str
    sender: UserMiniSchema
    recipient: UserMiniSchema


class ThreadSummarySchema(ConfigDictSetter):
    id: int
    created_at: datetime
    last_message: Optional[MessageSummarySchema] = None
