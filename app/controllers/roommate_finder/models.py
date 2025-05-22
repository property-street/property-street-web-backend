from sqlalchemy import (
    Text, 
    Column, 
    Integer, 
    DateTime,
    func,
    ForeignKey,
    Enum as SqlalchemyEnum,
    CheckConstraint,
)
from sqlalchemy.orm import relationship

from .enums import RoomiesApplicationEnumChoice
from property_street_backend.config.postgres_connection_manager import Base


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

    # relationship to user
    user_id = Column(
        Integer,
        ForeignKey(
            'users.id',
            name='fk_roomies_application_users',
            ondelete = 'CASCADE'
        )
    )
    users = relationship(
        'User',
        back_populates = 'roomie_application',
        lazy = 'selectin',
        uselist = False
    )

    # relationship to Roommate finder
    roommate_finder_id = Column(
        Integer,
        ForeignKey(
            'roommate_finders.id',
            name='fk_roommate_applications',
            ondelete = 'RESTRICT'
        )
    )
    roommate_finder = relationship(
        'RoommateFinder',
        lazy = 'selectin',
        back_populates='roomies_application',
        uselist = False,
    )


class RoommateFinder(Base):
    __tablename__ = 'roommate_finders'

    id = Column(Integer, index=True, primary_key=True)
    max_roomies = Column(Integer, default=1, nullable=False)
    extra_conditions = Column(Text)

    room_images_id = Column(
        Integer,
        ForeignKey(
            'cloud_image_details.id',
            name = "fk_roommate_finders_cloud_image_details",
            ondelete='RESTRICT' 
        ),
        nullable = False
    )
    room_images = relationship(
        'CloudImageDetail',
        lazy='selectin',
        back_populates= 'roommate_finder'
    )

    # requester info
    requester_id = Column(
        Integer,
        ForeignKey(
            'users.id',
            name='fk_roommate_finders_users',
            use_alter = True,
            ondelete='CASCADE'
        ),
        nullable = False
    )
    requester = relationship(
        'User',
        lazy='selectin',
        back_populates='roomate_finder',
        uselist = False
    )
    
    # relationship to area
    area_id = Column(
        Integer,
        ForeignKey(
            'areas.id',
            name = 'fk_roommate_finders_area',
            ondelete = 'RESTRICT'
        ),
        nullable = False
    ) 
    area = relationship(
        'Area',
        lazy = 'selectin',
        back_populates='roommate_finder',
        uselist=False,   
    )

    # relationship to roomie application
    roomies_application = relationship(
        'RoomieApplication',
        lazy='selectin',
        back_populates='roommate_finder'
    )


    __table_args__ = (
        CheckConstraint("max_roomies <= 10", name="check_max_roomies"),
        CheckConstraint("length(extra_conditions) <= 500", name="check_max_condition_length"),
    )