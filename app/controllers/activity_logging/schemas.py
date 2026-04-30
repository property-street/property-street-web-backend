from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from property_street_backend.app.controllers.activity_logging.enums import ActivityStatusChoice


class ActivityLogCreateSchema(BaseModel):
    action: str = Field(..., description="Action name")
    status: ActivityStatusChoice = Field(default=ActivityStatusChoice.pending)
    description: Optional[str] = None
    method: Optional[str] = None
    endpoint: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_body: Optional[str] = None
    response_status_code: Optional[int] = None
    response_time_ms: Optional[int] = None


class ActivityLogResponseSchema(BaseModel):
    id: int
    user_id: int
    action: str
    status: ActivityStatusChoice
    description: Optional[str] = None
    method: Optional[str] = None
    endpoint: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_body: Optional[str] = None
    response_status_code: Optional[int] = None
    response_time_ms: Optional[int] = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class ActivityLogListResponseSchema(BaseModel):
    total: int
    count: int
    page: int
    size: int
    items: List[ActivityLogResponseSchema]

    model_config = ConfigDict(from_attributes=True)


class ActivityStatisticsSchema(BaseModel):
    total_activities: int
    successful: int
    failed: int
    pending: int
    error: int
    most_common_action: Optional[str] = None
    success_rate: float

    model_config = ConfigDict(from_attributes=True)
