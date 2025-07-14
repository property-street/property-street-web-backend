from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from property_street_backend.app.schemas import ConfigDictSetter

class CloudImageSchema(ConfigDictSetter):
    secure_url: str


class UserMiniSchema(ConfigDictSetter):
    id: int
    first_name: str
    profile_avatar: Optional[CloudImageSchema] = None


class MessageSummarySchema(ConfigDictSetter):
    id: int
    fmt_msg_txt: Optional[str] = None
    additional_metadata: Optional[str] = None
    timestamp: int
    status: str
    sender: UserMiniSchema
    recipient: UserMiniSchema


class ThreadSummarySchema(ConfigDictSetter):
    id: int
    created_at: datetime
    last_message: Optional[MessageSummarySchema] = None
