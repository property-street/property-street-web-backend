"""
Two-factor authentication models.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from property_street_backend.app.models import Base


class TwoFactorAuth(Base):
    """
    Model for storing two-factor authentication settings and secrets.
    """
    __tablename__ = "two_factor_auth"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), unique=True, nullable=False)
    is_enabled = Column(Boolean, default=False)
    secret_key = Column(String, nullable=True)  # TOTP secret
    backup_codes = Column(String, nullable=True)  # Comma-separated backup codes
    method = Column(String, default="totp")  # totp or sms
    phone_number = Column(String, nullable=True)
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="two_factor_auth")


class TwoFactorAuthLog(Base):
    """
    Model for logging two-factor authentication attempts.
    """
    __tablename__ = "two_factor_auth_log"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    attempt_type = Column(String)  # setup, verify, failed_attempt
    success = Column(Boolean, default=False)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
