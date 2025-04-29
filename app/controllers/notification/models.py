from property_street_backend.config.postgres_connection_manager import Base
from sqlalchemy import (
    Integer,
    Column,
    String,
    ForeignKey,
    BigInteger,
    Enum as SQLAlchemyEnum
)
from sqlalchemy.orm import relationship

from .enum import NotificationStateChoice

class Notification(Base):
    __tablename__ = 'notifications'

    id = Column(Integer, primary_key=True, index=True)

    timestamp = Column(BigInteger, nullable=False)
    n_type = Column(String)
    n_serialized_obj = Column(String)
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