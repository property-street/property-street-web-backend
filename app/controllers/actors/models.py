from sqlalchemy import (
    Column, 
    Integer, 
    String,
    ForeignKey, 
    Boolean, 
    JSON, 
    Enum as SQLAlchemyEnum, 
    func,
    DateTime,
    event,
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncSession

from .enums import (
    UserRoleChoice,
    ClientGenderChoice,
)
from property_street_backend.config.postgres_connection_manager import Base
from property_street_backend.app.controllers.ratings.utils import AggregateRatingAClass


class Agent(AggregateRatingAClass):
    __tablename__ = 'agents'

    id = Column(
        Integer, 
        primary_key=True, 
        index=True,
        autoincrement=True,
    )
    
    # reverse relationship with the User model
    user = relationship(
        'User', 
        back_populates='agent_profile',
        uselist=False  # explicitly tell SQLAlchemy it's a one-to-one
    )
    
    # Reverse relationship to Asset (cascade on delete)
    assets = relationship(
        'Asset',
        back_populates='agent',
        cascade="all, delete-orphan",  # Cascade deletion from Agent to Asset
        lazy="selectin",  # Ensures relationship loads in async contexts

    )
   
   # many-to-many relationship to AssetRequest
    resolved_asset_requests = relationship(
        'AssetRequest',
        secondary='request_agent_association',
        lazy='selectin',
        back_populates = 'resolvers'
    )

    # relationship to ratings
    ratings = relationship(
        'Rating',
        lazy='selectin',
        back_populates = 'agent'
    )


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    first_name = Column(String)
    last_name = Column(String)
    other_names = Column(String)
    gender = Column(
        SQLAlchemyEnum(ClientGenderChoice, name='client_gender_choice')
    )
    account_status = Column(String, default="Active")
    misc = Column(JSON, default=dict, nullable=True)
    user_role = Column(
        SQLAlchemyEnum(UserRoleChoice, name='user_role_choice'),
        nullable=False,
        default=UserRoleChoice.user
    )
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)

    # dates
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # One-to-one relationship for cover image (no cascade)
    profile_avatar_id = Column(
        Integer, 
        ForeignKey(
            'cloud_image_details.id', 
            name='fk_user_profile_avatar_id', 
            use_alter=True,
            ondelete='SET NULL'
        ), 
        nullable=True
    )
    profile_avatar = relationship(
        'CloudImageDetail', 
        back_populates='user',
        uselist=False, # explicitly tell SQLAlchemy it's a one-to-one
        foreign_keys=[profile_avatar_id],
        lazy="selectin",  # Ensures relationship loads in async contexts
    )
  
    # Foreign key to Agent for one-to-one relationship (nullable until user becomes agent)
    agent_profile_id = Column(
        Integer, 
        ForeignKey(
            'agents.id', 
            name='fk_users_agent_profile_id', 
            use_alter=True, 
            ondelete='SET NULL'
        ), 
        unique=True, 
        nullable=True
    )
    agent_profile = relationship(
        'Agent', 
        back_populates = 'user',
        uselist=False, # explicitly tell SQLAlchemy it's a one-to-one
        foreign_keys=[agent_profile_id],
        lazy="selectin",  # Ensures relationship loads in async contexts
    )

    # relationship to chat session
    chat_session = relationship(
        'ChatSession', 
        back_populates = 'user',
        lazy="selectin",  # Ensures relationship loads in async contexts
    )

    # many to many relationship with thread
    threads = relationship(
        'Thread',
        secondary='threads_participants_association',
        back_populates='participants',
        lazy='selectin'
    )
    
    # Relationships for sent and received messages
    sent_messages = relationship(
        'Message',
        foreign_keys='Message.sender_id',
        back_populates='sender',
        lazy='selectin'
    )
    received_messages = relationship(
        'Message',
        foreign_keys='Message.recipient_id',
        back_populates='recipient',
        lazy='selectin'
    )

    # user settings relationship
    user_settings = relationship(
        'UserSetting',
        back_populates = 'user',
        lazy = 'selectin',
        uselist = False,
    )

    # google oauth details relationship
    google_oauth_detail = relationship(
        'GoogleOAuthDetail',
        back_populates = 'user',
        lazy = 'selectin',
        uselist = False,
    )

        # Reverse relationship to the CartItem
    
    # relationship to CartItem
    cart_items = relationship(
        'CartItem', 
        back_populates='user',
        cascade="all, delete-orphan", # cascade from User to CartItem
        lazy="selectin",  # Ensures relationship loads in async contexts
    )

    # relationship to AssetRequest
    requested_assets = relationship(
        'AssetRequest',
        back_populates = 'requester',
        lazy = 'selectin'
    )

    # relationship to notification
    notifications = relationship(
        'Notification',
        lazy='selectin',
        back_populates = 'user'
    )

    # one-to-many relationship to rooommates_finder
    roommates_finder = relationship(
        'RoommateFinder',
        lazy='selectin',
        back_populates = 'requester',
    )

    # many-to-many relationship to rooomies_application
    roomies_application = relationship(
        'RoomieApplication',
        secondary = 'roomies_application_roomies_applicants_association',
        lazy='selectin',
        back_populates = 'roomie_applicants',
    )

    # method for a user to become an agent
    async def become_agent(self, session: AsyncSession):
        """Method to convert a user into an agent."""
        if not self.agent_profile:
            # Create a new Agent instance associated with this user
            agent = Agent(user=self)
            session.add(agent)
            await session.flush()  # Ensures the new `agent` has an `id` before committing
            await session.commit()
            await session.refresh(self)  # Refresh `self` to update the `agent_profile`


@event.listens_for(User, 'before_insert')
# Listen for the 'before_insert' event to set updated_at
def set_updated_at_before_insert(mapper, connection, target):
    target.updated_at = func.now()