from pydantic import (
    BaseModel, 
)
from typing import Literal, Optional
from property_street_backend.app.schemas import ConfigDictSetter


class MessageSchema(ConfigDictSetter):
    id: int
    recipient_id: int
    sender_id: int
    status: Literal['unsent', 'sent', 'delivered', 'read']
    fmt_msg: dict
    server_timestamp_ms: int
    thread_id: int


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