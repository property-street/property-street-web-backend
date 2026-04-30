from sqlalchemy import (
    func,
    Column, 
    Integer, 
    String,
    ForeignKey, 
    Boolean, 
    JSON, 
    Enum as SQLAlchemyEnum, 
    DateTime,
    event,
)
from sqlalchemy.future import select
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import ARRAY

from .enums import (
    UserRoleChoice,
    ClientGenderChoice,
)
from .mixin import UniqueIDArrayMixin
from property_street_backend.config.settings import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
)
from property_street_backend.app.controllers.auth import verify_password
from property_street_backend.config.postgres_connection_manager import Base
from property_street_backend.app.controllers.assets.model_utils import UserAssetAbsCls
from property_street_backend.app.controllers.ratings.utils import AggregateRatingAClass

class User(AggregateRatingAClass, UniqueIDArrayMixin, UserAssetAbsCls):
    __tablename__ = 'users'

   # many-to-many relationship to AssetRequest
    resolved_asset_requests = relationship(
        'AssetRequest',
        secondary='request_agent_association',
        lazy='selectin',
        back_populates = 'resolvers'
    )


    # relationship to ratings
    agent_ratings = relationship(
        'Rating',
        lazy='selectin',
        back_populates = 'agent',
        foreign_keys="Rating.agent_id",
    )

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String, nullable=True)
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
    settings = relationship(
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

    # relationship to ratings
    ratings = relationship(
        'Rating',
        lazy='selectin',
        back_populates = 'rater',
        foreign_keys="Rating.rater_id"
    )

    cached_roomies_application_ids = Column(ARRAY(Integer), default=list)
    array_field_name = "cached_roomies_application_ids"
    

    # method for a user to become an agent
    async def become_agent(self, session: AsyncSession):
        """Method to convert a user into an agent."""
        if not self.user_role == 'agent':
            self.user_role = UserRoleChoice.agent
            session.add(self)
            await session.commit()
    
@event.listens_for(User, "before_insert")
def prevent_multiple_admins(mapper, connection, target):
    if not target.is_admin:
        return
    
    if (target.email != ADMIN_EMAIL) or not verify_password(ADMIN_PASSWORD, target.password_hash):
        raise ValueError("Unauthorized admin creation attempt detected.")
    
    # Ensure no existing admin
    existing_admin = connection.execute(
        select(User).where(User.is_admin == True)
    ).scalar_one_or_none()
    if existing_admin:
        raise ValueError("An admin user already exists. Only one admin is allowed.")

@event.listens_for(User, 'before_insert')
# Listen for the 'before_insert' event to set updated_at
def set_updated_at_before_insert(mapper, connection, target):
    target.updated_at = func.now()


class SocialLog(Base):
    __tablename__ = 'social_logs'

    id  = Column(Integer, index=True, primary_key=True)

    title = Column(String(1024))
    description = Column(String)
    media_urls = Column(ARRAY(String), default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user_id = Column(
        Integer,
        ForeignKey(
            'users.id',
            name='fk_social_logs_user_id_users',
            ondelete='CASCADE',
        ),
        nullable=False
    )
    user = relationship(
        User,
        backref='social_logs',
        lazy='selectin',
        uselist=False
    )
    