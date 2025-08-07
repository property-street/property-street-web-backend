from datetime import datetime
from typing import Optional

from .schemas import MessageSchema
from property_street_backend.app.schemas import ConfigDictSetter


class CloudImageSchema(ConfigDictSetter):
    secure_url: str


class MessageSummarySchema(MessageSchema):
    pass


class ThreadSummarySchema(ConfigDictSetter):
    id: int
    created_at: datetime
    last_message: Optional[MessageSummarySchema] = None
