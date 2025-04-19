from property_street_backend.app.database import Base
from sqlalchemy import (
    Integer,
    Column,
    String,
    ForeignKey,
    BigInteger,
    Enum as SQLAlchemyEnum
)

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
    user = Column(
        'User',
        lazy = 'selectin',
        useList = False,
        back_populates = 'notifications'
    )