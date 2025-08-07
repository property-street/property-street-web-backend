from pydantic import (
    BaseModel, 
    field_validator
)
from typing import Literal, Optional

from property_street_backend.app.schemas import ConfigDictSetter
from property_street_backend.app.models import User, CloudImageDetail

class UserMiniSchema(ConfigDictSetter):
    id: int
    username: str
    user_role: str
    profile_avatar: Optional[dict] = None
    
    @field_validator('profile_avatar', mode='before')
    def transform_field_validator(cls, value):
        if isinstance(value, CloudImageDetail) and hasattr(value, 'secure_url'):
            return {'url': value.secure_url}
        return None


class MessageSchema(ConfigDictSetter):
    id: int
    fmt_msg: dict
    server_timestamp_ms: int
    status: str #Literal['unsent', 'sent', 'delivered', 'read']
    msg_type: Optional[str]
    thread_id: int
    sender_id: int
    sender: UserMiniSchema
    recipient_id: int
    recipient: UserMiniSchema


class ChatObjectSchema(BaseModel):
    pass


class CachedMessageSchema(MessageSchema):
    id: Optional[int] = None
    server_timestamp_ms: Optional[int] = None

    category: Literal['chat'] = 'chat'
    msg_type: Literal['outbound_message','incoming_message', 'delivered_message', 'read_message', 'completed']
    
    thread_id: Optional[int] = None
    ui_inbound_timestamp_ms: Optional[int] = None
    ui_outbound_timestamp_ms: Optional[int] = None