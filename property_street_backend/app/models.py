from sqlalchemy import (
    Column, 
    Integer, 
    String,
    ForeignKey, 
    Date, 
    Boolean, 
    JSON, 
    Text, 
    DateTime,
    Enum as SQLAlchemyEnum, 
    event,
    func,
    Numeric
)
from sqlalchemy.future import select
from sqlalchemy import types as _types
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.enums import (
    EmailManagementReasonChoice,
    ClientTypeChoice,
    AssetCategoryChoice,
)
from property_street_backend.app.database import Base

#models
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    first_name = Column(String)
    last_name = Column(String)
    other_names = Column(String)
    date_of_birth = Column(Date)
    country_of_origin = Column(String)
    account_status = Column(String, default="Active")
    misc = Column(JSON, default=dict, nullable=True)
    client_type = Column(SQLAlchemyEnum(ClientTypeChoice, name='client_type_choice'), nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    
    # Reverse relationships
    profile_avatar = relationship(
        'CloudImageDetail', 
        back_populates='user', 
        uselist=False
    ) 
    


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

        # Listen for the 'before_insert' event to set updated_at
    
#@event.listens_for(EmailManagementModel, 'before_insert')
#def set_updated_at_before_insert(mapper, connection, target):
#    target.updated_at = func.now()


class MediaFile(Base):
    __tablename__ = 'media_files'

    id = Column(Integer, primary_key=True, index=True)
    file_url = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    hash = Column(String, unique=True, nullable=False)

    # foreign keys
    asset_id = Column(Integer, ForeignKey('assets.id'))
    feature_id = Column(Integer, ForeignKey('asset_features.id'))
    user_id = Column(Integer, ForeignKey('users.id'))

    # reverse relationship
    asset = relationship('Asset', back_populates='media_files')
    asset_feature = relationship('AssetFeature', back_populates='media_files')
    user = relationship(
        'User', 
        back_populates='media_file', 
        uselist=False
    ) 
    # uselist=False -> makes the foreignkey
    # a one to one relationship; 

class CloudImageDetail(Base):
    __tablename__ = 'cloud_image_details'

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(String, nullable=False)
    created_at = Column(String, nullable=False)  # Format: ISO 8601, e.g., "2024-09-02T14:42:48Z"
    format = Column(String, nullable=False)
    bytes = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    public_id = Column(String, unique=True, nullable=False)
    secure_url = Column(String, nullable=False)
    width = Column(Integer, nullable=False)

    # foreign keys
    asset_id = Column(Integer, ForeignKey('assets.id'))
    feature_id = Column(Integer, ForeignKey('asset_features.id'))
    user_id = Column(Integer, ForeignKey('users.id'))

    # reverse relationship
    asset = relationship('Asset', back_populates='cloud_image_details')
    asset_feature = relationship('AssetFeature', back_populates='cloud_image_details')
    user = relationship(
        'User', 
        back_populates='cloud_image_detail', 
        uselist=False
    ) 
    # uselist=False -> makes the foreignkey
    # a one to one relationship; 


class Asset(Base):
    __tablename__ = 'assets'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    country = Column(String, nullable=False)
    address = Column(String, nullable=False)
    currency = Column(String, nullable=False)
    amount = Column(Numeric, nullable=False)
    description = Column(Text, nullable=True)
    has_features = Column(Boolean, default=False)
    tags = Column(String, nullable=True)
    availability = Column(Boolean, default=True)

    # enums
    category = Column(SQLAlchemyEnum(AssetCategoryChoice), nullable=False)
    
    # foreignkey
    user_id = Column(Integer, ForeignKey('users.id'))

    # reverse relationship
    user = relationship('User', back_populates='assets')
    media_files = relationship('MediaFile', back_populates='asset')
    cloud_image_details = relationship('CloudImageDetail', back_populates='asset')
    features = relationship('AssetFeature', back_populates='asset')



class AssetFeature(Base):
    __tablename__ = 'asset_features'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)

    # foreign keys
    asset_id = Column(Integer, ForeignKey('assets.id'))

    # reverse relationship
    asset = relationship('Asset', back_populates='features')
    media_files = relationship('MediaFile', back_populates='asset_feature')
    cloud_image_details = relationship('CloudImageDetail', back_populates='asset_feature')
