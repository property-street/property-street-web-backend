"""
OAuth schemas for request/response validation.
"""
from typing import Optional
from pydantic import BaseModel, EmailStr


class GoogleUserData(BaseModel):
    """Schema for Google OAuth user data."""
    email: EmailStr
    sub: str
    picture: Optional[str] = None
    name: Optional[str] = None


class OAuthErrorResponse(BaseModel):
    """Schema for OAuth error responses."""
    error: str
    error_description: Optional[str] = None
