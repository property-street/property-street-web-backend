from sqlalchemy import (
    Column, 
    Integer, 
    String,
    ForeignKey, 
    Date, 
    Boolean, 
    JSON, 
    Table,
    Enum as SQLAlchemyEnum, 
    func,
    DateTime,
    event,
    ARRAY,
)
from sqlalchemy.future import select
from sqlalchemy import types as _types
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncSession


from .models_helper import AbstractCloudImage
from property_street_backend.app.enums import (
    EmailManagementReasonChoice,
    ClientTypeChoice,
    ClientGenderChoice,
)
from property_street_backend.config.postgres_connection_manager import Base
from property_street_backend.app.controllers.cart.models import CartItem
from property_street_backend.app.controllers.chat.models import (
    Thread,
    ChatSession,
    Message,
) 
from property_street_backend.app.controllers.assets.models import (
    Tag,
    Asset,
    AssetFeature,
    AssetCloudImage,
) 
from property_street_backend.app.controllers.ratings.models import Rating
from property_street_backend.app.controllers.notification.models import Notification
from property_street_backend.app.controllers.asset_request.models import AssetRequest
from property_street_backend.app.controllers.ratings.utils import AggregateRatingAClass
from property_street_backend.app.controllers.roommate_finder.models import RoomieApplication, RoommateFinder




# asset-tag Association Table for many-to-many relationship
asset_tag_association = Table(
    'asset_tag_association',
    Base.metadata,
    Column(
        'asset_id', 
        Integer, 
        ForeignKey(
            'assets.id', 
            name='fk_asset_tag_association_asset_id',
            ondelete='CASCADE'
        ), 
        primary_key=True
    ),
    Column(
        'tag_id', 
        Integer, 
        ForeignKey(
            'tags.id', 
            name='fk_asset_tag_association_tag_id',
            ondelete='RESTRICT'
        ), 
        primary_key=True
    )
)

# models

# cascade="all, delete-orphan"
# this specifies the operations that should "cascade" 
# from the parent object to the related child objects 
# (usually in a one-to-many or many-to-one relationship).

class EmailManagementModel(Base):
    __tablename__ = 'email_management_model'

    id = Column(String, primary_key=True, index=True)
    email_address = Column(String, nullable=True)
    email_code = Column(String(255), unique=True, nullable=True)
    email_code_time = Column(
        _types.TIMESTAMP(timezone=True),
        server_default=func.now(),  # Sets the default value on insert
        onupdate=func.now(),        # Updates the value on update
        nullable=True
    )
    email_link = Column(String, nullable=True)
    email_link_time = Column(
        _types.TIMESTAMP(timezone=True),
        server_default=func.now(),  # Sets the default value on insert
        onupdate=func.now(),        # Updates the value on update
        nullable=True
    )
    reason = Column(SQLAlchemyEnum(EmailManagementReasonChoice, name='email_management_reason_choice'), nullable=True)

    def __str__(self):
        return f"{self.email_address} - {self.reason.value}"

    @classmethod
    async def email_exists(cls, db_session: AsyncSession, email: str) -> bool:
        """
        Check if an instance with the given email address exists.

        Args:
        - db_session (AsyncSession): SQLAlchemy async session to use for the query.
        - email (str): The email address to check.

        Returns:
        - bool: True if an instance with the given email address exists, else False.
        """
        result = await db_session.execute(
            select(cls).filter(cls.email_address == email)
        )
        return result.scalars().first() is not None
    
    @classmethod
    async def check_email_code_exists(cls, db_session: AsyncSession, email_code_to_check: str) -> bool:
        """
        Check if a code exists in this model.

        Args:
        - db_session (AsyncSession): SQLAlchemy async session to use for the query.
        - email_code_to_check (str): The email code to check.

        Returns:
        - bool: True if an instance with the given email code exists, else False.
        """
        result = await db_session.execute(
            select(cls).filter(cls.email_code == email_code_to_check)
        )
        return result.scalars().first() is not None


class CloudImageDetail(AbstractCloudImage):  # Inherit the abstract base
    __tablename__ = 'cloud_image_details'

    # Reverse relationship to user
    user = relationship(
        'User', 
        back_populates='profile_avatar',
        uselist=False,  # explicitly tell SQLAlchemy it's a one-to-one
        lazy="selectin",  # Ensures relationship loads in async contexts
    )

    # Reverse relationship to Asset
    asset = relationship(
        'Asset', 
        back_populates='cover_image',
        uselist=False,  # explicitly tell SQLAlchemy it's a one-to-one 
        post_update=True,
        lazy="selectin",  # Ensures relationship loads in async contexts
    )

    roommates_finder_id = Column(
        Integer,
        ForeignKey(
            'roommates_finder.id',
            name = "fk_cloud_image_details_roommates_finder",
            ondelete='CASCADE' 
        )
    )
    # many-to-one relationship to roommate finder
    roommates_finder = relationship(
        'RoommateFinder',
        lazy = 'selectin',
        back_populates= 'room_images',
        uselist=False
    )


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
    client_type = Column(SQLAlchemyEnum(ClientTypeChoice, name='client_type_choice'), nullable=True)
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
    async def become_agent(self, session):
        """Method to convert a user into an agent."""
        if not self.agent_profile:
            # Create a new Agent instance associated with this user
            agent = Agent(user=self)
            session.add(agent)
            await session.flush()  # Ensures the new `agent` has an `id` before committing
            await session.commit()
            await session.refresh(self)  # Refresh `self` to update the `agent_profile`


class GoogleOAuthDetail(Base):
    __tablename__ = "google_oauth_details"

    id = Column(Integer, primary_key=True, index=True)
    google_id = Column(String, nullable=True)
    profile_picture = Column(String, nullable=True)
    
    user_id = Column(
        Integer, 
        ForeignKey(
            'users.id', 
            name='fk_google_oauth_details_users', 
            use_alter=True,
            ondelete='CASCADE'
        ), 
        nullable=False
    )
    user = relationship(
        'User', 
        back_populates='google_oauth_detail',
        uselist=False,  # explicitly tell SQLAlchemy it's a one-to-one 
        post_update=True,
        lazy="selectin",  # Ensures relationship loads in async contexts
    )


class UserSetting(Base):
    __tablename__ = 'user_settings'

    id = Column(Integer, primary_key=True, index=True)
    date_of_birth = Column(Date, nullable=True)
    country = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    address = Column(String, nullable=True)
    email_notification = Column(Boolean, default=True)
    push_notification = Column(Boolean, default=True)

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
        back_populates='user_settings',
        lazy='selectin',
        uselist = False,
    )


class Area(AggregateRatingAClass):
    __tablename__ = 'areas'

    id = Column(Integer, primary_key=True, index=True)
    
    # For international usage, consider using a library like pycountry or geopy for validating country/state/city combinations.
    country = Column(String, nullable=False) # e.g., Nigeria
    state_or_province = Column(String, nullable=False) # e.g., "California" or "Lagos"
    city_or_town = Column(String, nullable=False) # e.g., "San Francisco" or "Ikeja"
    county = Column(String) # US-based e.g., "Los Angeles County"
    street = Column(String) # e.g., "Market Street", "Ahmadu Bello Way"
    building_name_or_suite = Column(String) # e.g., "Apt 402"
    zip_or_postal_code = Column(String) # e.g., 500102


    asset = relationship(
        'Asset',
        back_populates='area',
        lazy = 'selectin',
        uselist=False
    )
    requested_asset = relationship(
        'AssetRequest',
        back_populates='area',
        lazy='selectin',
        uselist=False
    )

    ratings = relationship(
        'Rating',
        lazy='selectin',
        back_populates = 'area'
    )

    # relationship to roommate finder
    roommates_finder = relationship(
        'RoommateFinder',
        lazy='selectin',
        back_populates = 'area',
        uselist = False
    )




class AddOn(Base):
    __tablename__ = 'add_ons'

    id = Column(Integer, primary_key=True, index=True)
    tag_list = Column(ARRAY(String))  # Or JSON, based on your preference


models = [
    Tag,
    Asset,
    Thread,
    Rating,
    Message,
    CartItem,
    ChatSession,
    AssetRequest,
    Notification,
    AssetFeature,
    RoommateFinder, 
    AssetCloudImage, 
    RoomieApplication,
]

    

@event.listens_for(User, 'before_insert')
# Listen for the 'before_insert' event to set updated_at
def set_updated_at_before_insert(mapper, connection, target):
    target.updated_at = func.now()