from typing import Optional
from pydantic import BaseModel, ConfigDict

from .enums import NotificationTypeChoice, NotificationStateChoice

class FMTNOT(BaseModel):
    title: str
    text_content: Optional[str] = None
    media_urls: Optional[list] = None
    avatar: Optional[str] = None
    ref_model: Optional[str] = None
    ref_id: Optional[int] = None

class ModelFMTNOT(FMTNOT):
    ref_model: str
    ref_id: int

class NotificationResponse(BaseModel):
    id: int
    n_type: NotificationTypeChoice
    fmt_not: ModelFMTNOT
    n_status: NotificationStateChoice
    timestamp: float
    user_id: int

    model_config = ConfigDict(from_attributes=True)