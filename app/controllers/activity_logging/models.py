from sqlalchemy import Column, DateTime, Enum as SQLAlchemyEnum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from property_street_backend.config.postgres_connection_manager import Base
from property_street_backend.app.controllers.activity_logging.enums import ActivityStatusChoice


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(255), nullable=False, index=True)
    status = Column(
        SQLAlchemyEnum(ActivityStatusChoice, name="activity_status_choice"),
        default=ActivityStatusChoice.pending,
        nullable=False,
        index=True,
    )
    description = Column(Text, nullable=True)
    method = Column(String(10), nullable=True)
    endpoint = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    request_body = Column(Text, nullable=True)
    response_status_code = Column(Integer, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    activity_type = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=func.now(), index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", name="fk_activity_logs_user_id_users", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user = relationship("User", backref="activity_logs", uselist=False, lazy="selectin")

RequestLog = ActivityLog


class EventLog(Base):
    __tablename__ = "event_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    action = Column(String(255), nullable=False, index=True)
    status = Column(
        SQLAlchemyEnum(ActivityStatusChoice, name="event_status_choice"),
        default=ActivityStatusChoice.success,
        nullable=False,
        index=True,
    )
    description = Column(Text, nullable=True)
    affected_model = Column(String(100), nullable=True, index=True)
    affected_model_id = Column(Integer, nullable=True, index=True)
    affected_model_ids = Column(String(255), nullable=True)
    payload = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=func.now(), index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", name="fk_event_logs_user_id_users", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user = relationship("User", backref="event_logs", uselist=False, lazy="selectin")
