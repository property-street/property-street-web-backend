from sqlalchemy.orm import relationship             
from sqlalchemy import Column, Integer, String, Date, Boolean, ForeignKey, CheckConstraint

from property_street_backend.config.postgres_connection_manager import Base

class UserSetting(Base):
    __tablename__ = 'user_settings'

    id = Column(Integer, primary_key=True, index=True)
    date_of_birth = Column(Date, nullable=True)
    phone_number = Column(String, nullable=True)
    dial_code = Column(String)
    email_notification = Column(Boolean, default=True)
    push_notification = Column(Boolean, default=True)

    area_id = Column(
        Integer,
        ForeignKey(
            'areas.id',
            name = 'fk_user_settings_areas',
            ondelete = 'CASCADE'
        ) 
    )
    areas = relationship(
        'Area',
        lazy='selectin',
        back_populates = 'occupant',
        uselist = True
    )

    user_id = Column(
        Integer, 
        ForeignKey(
            'users.id', 
            name='fk_user_settings_users', 
            use_alter=True,
            ondelete='CASCADE'
        ), 
        nullable=False
    )
    user = relationship(
        'User',
        back_populates='settings',
        lazy='selectin',
        uselist = False,
    )
