from pydantic import (
    BaseModel, 
)
from typing import Literal, Optional

class ChatObjectSchema(BaseModel):
    # mandatory fields
    category: Literal['chat'] = 'chat'
    recipient_id: int
    sender_id: int
    msg_type: Literal['incoming_message', 'read_message']
    status: Literal['unsent', 'sent', 'delivered', 'read']
    fmt_msg_txt: str

    # optional fields
    unix_timestamp_ms: Optional[int] = None
    media_urls: Optional[str] = None
    db_id: Optional[int] = None
    thread_id: Optional[int] = None