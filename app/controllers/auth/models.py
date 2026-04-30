from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, func
from sqlalchemy.orm import backref, relationship

from property_street_backend.config.postgres_connection_manager import Base


class RefreshSession(Base):
    __tablename__ = "refresh_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", name="fk_refresh_sessions_user_id_users", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    access_token_hash = Column(String, nullable=True)
    token_hash = Column(String, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    user_agent = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    is_revoked = Column(Boolean, nullable=False, default=False)

    user = relationship(
        "User",
        backref=backref("refresh_sessions", passive_deletes=True),
        lazy="selectin",
        uselist=False,
    )


class RequestLog(Base):
    __tablename__ = "request_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", name="fk_request_logs_user_id_users", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    refresh_session_id = Column(
        Integer,
        ForeignKey("refresh_sessions.id", name="fk_request_logs_refresh_session_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action = Column(String, nullable=False)
    method = Column(String, nullable=False)
    endpoint = Column(String, nullable=False)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    response_status_code = Column(Integer, nullable=False)
    response_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User", lazy="selectin", uselist=False)
    refresh_session = relationship("RefreshSession", lazy="selectin", uselist=False)
