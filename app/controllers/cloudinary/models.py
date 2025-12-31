from sqlalchemy import (
    func,
    Column,
    String,
    Integer,
    DateTime,
)
from property_street_backend.config.postgres_connection_manager import Base


class CloudDeletionOutbox(Base):
    __tablename__ = "cloud_deletion_outbox"

    id = Column(Integer, primary_key=True)
    public_id = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime, default=func.now())
