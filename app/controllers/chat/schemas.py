from pydantic import (
    BaseModel, 
    field_validator
)
from typing import Literal, Optional, List, Any
from .enums import MessageTypes, MessageStatus
from property_street_backend.app.schemas import ConfigDictSetter
from property_street_backend.app.models_helper import CloudImageDetail
from property_street_backend.app.controllers.assets.schemas import CloudImageSchema

class UserMiniBase(BaseModel):
    id: int
    username: str
    user_role: str
    profile_avatar: Optional[dict] = None

class UserMiniSchema(UserMiniBase, ConfigDictSetter):
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
    media: List[CloudImageSchema] = []
    reactions: Optional[dict[str, List[UserMiniBase]]] = None
    additional_metadata: AdditionalMetadata
    ui_inbound_timestamp_ms: int
    ui_outbound_timestamp_ms: int


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
    """always use ...model_dump(exclude_unset=True)

    Args:
        MessageSchema (_type_): _description_
    """
    id: Optional[int] = None
    thread_id: Optional[int] = None
    thread_name: Optional[str] = None
    server_timestamp_ms: Optional[float] = None
    ui_order_index: Optional[float] = None     
    ui_timestamp_ms: Optional[float] = None
    # redundant
    category: Literal['chat'] = 'chat'
    thread_thumbnail: Optional[str] = None


# 🧠 However, if you want to mimic TS behavior exactly — i.e.
# 
# “may be omitted entirely” and “must be a string if present”,
# use this:
# from pydantic import BaseModel, Field
# 
# class Thread(BaseModel):
#     thread_name: str | None = Field(default=None)
# 
# And when parsing:
#
# Thread()  # OK → thread_name missing
# Thread(thread_name="Discussion")  # OK
# Thread(thread_name=None)  # Also OK (explicitly set None)
