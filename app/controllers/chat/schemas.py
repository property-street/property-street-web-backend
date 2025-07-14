from pydantic import (
    BaseModel, 
)
from typing import Literal, Optional

class ChatObjectSchema(BaseModel):
    # mandatory fields
    category: Literal['chat'] = 'chat'
    recipient_id: int
    sender_id: int
    msg_type: Literal['outbound_message','incoming_message', 'read_message']
    status: Literal['unsent', 'sent', 'delivered', 'read']
    fmt_msg_txt: Optional[str]
    text_content: str

    # optional fields
    unix_timestamp_ms: Optional[int] = None
    media_urls: Optional[str] = None
    db_id: Optional[int] = None
    thread_id: Optional[int] = None
    additional_metadata: Optional[str] = None