from sqlalchemy import (
    Column, 
    Integer, 
    String,
    ForeignKey, 
    Date, 
    Boolean, 
    Table,
    Enum as SQLAlchemyEnum, 
    func,
    ARRAY,
)
from sqlalchemy.future import select
from sqlalchemy import types as _types
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncSession


from .models_helper import AbstractCloudImage
from property_street_backend.app.enums import (
    EmailManagementReasonChoice,
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
from property_street_backend.app.controllers.actors.models import (
    User
) 
from property_street_backend.app.controllers.ratings.models import Rating
from property_street_backend.app.controllers.notification.models import Notification
from property_street_backend.app.controllers.asset_request.models import AssetRequest
from property_street_backend.app.controllers.ratings.utils import AggregateRatingAClass
from property_street_backend.app.controllers.roommate_finder.models import RoomieApplication, RoommateFinder
from property_street_backend.app.controllers.settings.models import UserSetting




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

    id = Column(Integer, primary_key=True, index=True)

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

    occupant = relationship(
        'UserSetting',
        lazy='selectin',
        back_populates='areas',
        uselist = False
    )


class AddOn(Base):
    __tablename__ = 'add_ons'

    id = Column(Integer, primary_key=True, index=True)
    tag_list = Column(ARRAY(String))  # Or JSON, based on your preference



models = [
    Tag,
    User,
    Asset,
    Thread,
    Rating,
    Message,
    ChatSession,
    UserSetting,
    AssetRequest,
    Notification,
    AssetFeature,
    RoommateFinder, 
    AssetCloudImage, 
    RoomieApplication,
]
