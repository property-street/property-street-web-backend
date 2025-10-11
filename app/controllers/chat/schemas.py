from pydantic import (
    BaseModel, 
    field_validator
)
from typing import Literal, Optional, List, Any
from .enums import MessageTypes, MessageStatus
from property_street_backend.app.schemas import ConfigDictSetter
from property_street_backend.app.models_helper import CloudImageDetail
from property_street_backend.app.controllers.assets.schemas import CloudImageSchema

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

class AdditionalMetadata(BaseModel):
    edited: bool = False
    pinned: bool = False

class FMTMSG(BaseModel):
    text_content: str = ''
    media: CloudImageSchema = []
    reactions: Optional[dict[str, int]] = None
    additional_metadata: AdditionalMetadata


class MessageSchema(ConfigDictSetter):
    id: int
    fmt_msg: FMTMSG
    server_timestamp_ms: float
    status: MessageStatus
    msg_type: MessageTypes
    thread_id: int
    sender_id: int
    sender: UserMiniSchema
    recipient_id: int
    recipient: UserMiniSchema


class CachedMessageSchema(MessageSchema):
    id: Optional[int] = None
    server_timestamp_ms: Optional[float] = None

    category: Literal['chat'] = 'chat'
    
    thread_id: Optional[int] = None
    ui_inbound_timestamp_ms: Optional[float] = None
    ui_outbound_timestamp_ms: Optional[float] = None