from sqlalchemy import (
    func,
    Float,
    Column,
    Integer,
    DateTime,
    ForeignKey,
    Enum as SQLAlchemyEnum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from .enums import NotificationStateChoice, NotificationTypeChoice
from property_street_backend.config.postgres_connection_manager import Base

class Notification(Base):
    __tablename__ = 'notifications'

    id = Column(Integer, primary_key=True, index=True)

    # created_at = Column(DateTime(timezone=True), server_default=func.now())
    timestamp = Column(Float, nullable=False)
    n_type = Column(
        SQLAlchemyEnum(NotificationTypeChoice, name='notification_type_choice'), 
        default='generic',
        nullable=False
    )
    fmt_not = Column(JSONB)
    n_status = Column(
        SQLAlchemyEnum(NotificationStateChoice, name='notification_state_choice'), 
        default='undelivered',
        nullable=False
    )

    user_id = Column(
        Integer,
        ForeignKey(
            'users.id',
            name='fk_notifications_users',
            ondelete='CASCADE',
            use_alter=True
        ),
        nullable=False
    )
    user = relationship(
        'User',
        lazy = 'selectin',
        uselist = False,
        back_populates = 'notifications'
    )