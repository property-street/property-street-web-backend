from sqlalchemy import (
    Text, 
    Column, 
    Integer, 
    DateTime,
    func,
    ForeignKey,
    Enum as SqlalchemyEnum,
    CheckConstraint,
    Table
)
from sqlalchemy.orm import relationship

from .enums import RoomiesApplicationEnumChoice
from property_street_backend.config.postgres_connection_manager import Base

# message-thread Association Table for many-to-many relationship
roomies_application_roomies_applicants_association = Table(
    'roomies_application_roomies_applicants_association',
    Base.metadata,
    Column(
        'roomies_application_id', 
        Integer, 
        ForeignKey(
            'roomies_application.id', 
            name='fk_roomies_application_users',
            ondelete='RESTRICT'
        ), 
        primary_key=True
    ),
    Column(
        'user_id', 
        Integer, 
        ForeignKey(
            'users.id', 
            name='fk_users_roomies_application',
            ondelete='CASCADE'
        ), 
        primary_key=True
    ),
)


class RoomieApplication(Base):
    __tablename__ = 'roomies_application'

    id = Column(Integer, index = True, primary_key = True)
    date_applied = Column(DateTime(timezone=True), server_default=func.now())
    datetime_approved_or_rejected = Column( DateTime(timezone=True) )
    status = Column( 
        SqlalchemyEnum(RoomiesApplicationEnumChoice, name='roomies_application_status_choice'),
        default = 'pending',
        nullable = False
    )

    # relationship to user/applicants
    roomie_applicants = relationship(
        'User',
        secondary='roomies_application_roomies_applicants_association',
        back_populates = 'roomies_application',
        lazy = 'selectin',
    )

    # relationship to Roommate finder
    roommate_finder_id = Column(
        Integer,
        ForeignKey(
            'roommates_finder.id',
            name='fk_roommate_applications',
            ondelete = 'RESTRICT'
        )
    )
    roommates_finder = relationship(
        'RoommateFinder',
        lazy = 'selectin',
        back_populates='roomies_application',
        uselist = False,
    )


class RoommateFinder(Base):
    __tablename__ = 'roommates_finder'

    id = Column(Integer, index=True, primary_key=True)
    max_roomies = Column(Integer, default=1, nullable=False)
    extra_conditions = Column(Text)
    category = Column(Text, nullable=False)

    # one-to-many relationship to cloud_image_details
    room_images = relationship(
        'CloudImageDetail',
        lazy='selectin',
        back_populates= 'roommates_finder'
    )

    # requester info
    requester_id = Column(
        Integer,
        ForeignKey(
            'users.id',
            name='fk_roommates_finder_users',
            use_alter = True,
            ondelete='CASCADE'
        ),
        nullable = False
    )
    requester = relationship(
        'User',
        lazy='selectin',
        back_populates='roommates_finder',
        uselist = False
    )
    
    # relationship to area
    area_id = Column(
        Integer,
        ForeignKey(
            'areas.id',
            name = 'fk_roommates_finder_area',
            ondelete = 'RESTRICT'
        ),
        nullable = False
    ) 
    area = relationship(
        'Area',
        lazy = 'selectin',
        back_populates='roommates_finder',
        uselist=False,   
    )

    # relationship to roomie application
    roomies_application = relationship(
        'RoomieApplication',
        lazy='selectin',
        back_populates='roommates_finder'
    )


    __table_args__ = (
        CheckConstraint("max_roomies <= 10", name="check_max_roomies"),
        CheckConstraint("length(extra_conditions) <= 500", name="check_max_condition_length"),
    )