from sqlalchemy import (
    Text, 
    func,
    Table,
    event,
    Column, 
    Integer, 
    DateTime,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    Enum as SqlalchemyEnum,
)
from sqlalchemy import literal
from sqlalchemy.orm import Session
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import array, INTEGER

from .enums import RoomiesApplicationEnumChoice
from property_street_backend.app.controllers.actors.models import User
from property_street_backend.config.postgres_connection_manager import Base

class RoomieApplication(Base):
    __tablename__ = 'roomies_application'

    id = Column(Integer, index = True, primary_key = True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    datetime_approved_or_rejected = Column( DateTime(timezone=True) )
    status = Column( 
        SqlalchemyEnum(RoomiesApplicationEnumChoice, name='roomies_application_status_choice'),
        default = 'pending',
        nullable = False
    )

    # relationship to user/applicants
    applicant_id = Column(
        Integer,
        ForeignKey(
            'users.id',
            name='fk_roomies_application',
            use_alter=True,
            ondelete='CASCADE'
        ),
        nullable=False
    )
    roomie_applicant = relationship(
        'User',
        backref = 'roomies_application',
        lazy = 'selectin',
        uselist=False
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
        backref='roomies_application',
        uselist = False,
    )

    # Enforces Proxy Constraint; 1 User per Roommate_finder in a multi-linked relationship
    __table_args__ = (
        UniqueConstraint("roommate_finder_id", "applicant_id", name="uq_applicant_per_finder"),
    )

"""
@event.listens_for(Session, "after_flush")
def after_flush(session, flush_context):
    for obj in session.new:
        if isinstance(obj, RoomieApplication):
            # get applicant (ORM object)
            applicant = obj.roomie_applicant  
            if applicant:
                applicant.add_id(obj.roommate_finder_id)
                session.add(applicant)  # mark as dirty so it updates
"""

# When application is created → add RF ID to applicant
@event.listens_for(RoomieApplication, "after_insert")
def after_application_insert(mapper, connection, target):
    user_table = User.__table__

    # Build an integer array literal with the roommate_finder_id
    new_array = array([literal(target.roommate_finder_id, type_=INTEGER)])

    stmt = (
        user_table.update()
        .where(user_table.c.id == target.applicant_id)
        .values(
            cached_roomies_application_ids=(
                User.cached_roomies_application_ids.op("||")(new_array)
            )
        )
    )
    connection.execute(stmt)


# When an application is deleted
@event.listens_for(RoomieApplication, "after_delete")
def after_application_delete(mapper, connection, target):
    user_table = User.__table__
    stmt = (
        user_table.update()
        .where(user_table.c.id == target.applicant_id)
        .values(
            cached_roomies_application_ids=func.array_remove(
                User.cached_roomies_application_ids,
                target.roommate_finder_id
            )
        )
    )
    connection.execute(stmt)


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
        backref='roommates_finder',
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


    __table_args__ = (
        CheckConstraint("max_roomies <= 10", name="check_max_roomies"),
        CheckConstraint("length(extra_conditions) <= 500", name="check_max_condition_length"),
    )