from pydantic import (
    BaseModel, 
)
from typing import Literal, Optional

class ChatObjectSchema(BaseModel):
    category: Literal['chat'] = 'chat'
    recipient_id: int
    sender_id: int
    msg_type: Literal['incoming_message', 'read_message']
    status: Literal['unsent', 'sent', 'delivered', 'read']
    unix_timestamp_ms: int
    fmt_msg_txt: str
    db_id: Optional[int]
    thread_id: Optional[int]