"""
Two-factor authentication schemas.
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class Enable2FARequest(BaseModel):
    """Request to enable 2FA"""
    method: str  # totp or sms


class Verify2FARequest(BaseModel):
    """Request to verify 2FA code"""
    code: str
    user_id: int


class TwoFactorAuthSchema(BaseModel):
    """Two-factor auth response schema"""
    id: int
    user_id: int
    is_enabled: bool
    method: str
    verified: bool
    created_at: datetime

    class Config:
        from_attributes = True
