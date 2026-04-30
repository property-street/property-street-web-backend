from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RefreshSessionSchema(BaseModel):
    id: int
    user_id: int
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_revoked: bool
    expires_at: datetime
    last_used_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None
    logout_all_sessions: bool = False
