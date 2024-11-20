from sqlalchemy import (
    Column, 
    Integer, 
    String,
    ForeignKey, 
    Date, 
    Boolean, 
    JSON, 
    Text, 
    Table,
    Enum as SQLAlchemyEnum, 
    func,
    Numeric,
    DateTime,
    event,
)
from sqlalchemy.future import select
from sqlalchemy import types as _types
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.declarative import declared_attr


from property_street_backend.app.enums import (
    EmailManagementReasonChoice,
    ClientTypeChoice,
    AssetCategoryChoice,
)
from property_street_backend.app.database import Base


# abstract class dependency for models with cloud images fields
class AbstractCloudImage(Base):
    __abstract__ = True  # Ensure this class is not mapped to its own table

    id = Column(Integer, primary_key=True, index=True)
    format = Column(String, nullable=False)
    cloud_asset_id = Column(String, nullable=False)
    bytes = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    public_id = Column(String, unique=True, nullable=False)
    secure_url = Column(String, nullable=False)
    width = Column(Integer, nullable=False)

    # dates
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Optionally, if you want dynamic table names, you can define a declared_attr:
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()  # Use class name as table name




# Association Table for many-to-many relationship
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


class Agent(Base):
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


class Tag(Base):
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

    # Relationship
    assets = relationship(
        'Asset', 
        secondary='asset_tag_association', 
        back_populates='tags',
        lazy="selectin",  # Ensures relationship loads in async contexts

    )


class Asset(Base):
    __tablename__ = 'assets'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    country = Column(String, nullable=False)
    address = Column(String, nullable=False)
    currency = Column(String, nullable=False)
    status = Column(String, nullable=False)
    amount = Column(Numeric, nullable=False)
    lease_duration = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    has_features = Column(Boolean, default=False)
    availability = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Enums
    #category= Column(SQLAlchemyEnum(AssetCategoryChoice, name='asset_category_choice'), nullable=True)
    category= Column(String, nullable=False)

    # Foreign key relationship to Agent
    agent_id = Column(
        Integer, 
        ForeignKey(
            'agents.id', 
            name='fk_assets_agent_id', 
            ondelete='CASCADE'
        )
    )
    agent = relationship(
        'Agent', 
        back_populates='assets',
        lazy="selectin",  # Ensures relationship loads in async contexts

    )

    # One-to-one relationship for cover image (no cascade)
    cover_image_id = Column(
        Integer, 
        ForeignKey(
            'cloud_image_details.id', 
            name='fk_assets_cover_image_id', 
            use_alter=True, 
            ondelete='SET NULL'
        ), 
        nullable=True
    )
    cover_image = relationship(
        'CloudImageDetail', 
        back_populates='asset',
        uselist=False, # explicitly tell SQLAlchemy it's a one-to-one
        foreign_keys=[cover_image_id], 
        post_update=True,
        lazy="selectin",  # Ensures relationship loads in async contexts
    )
    
    # Many-to-many relationship with Tag
    tags = relationship(
        'Tag', 
        secondary='asset_tag_association', 
        back_populates='assets',
        lazy="selectin",  # Ensures relationship loads in async contexts
    )

    # Reverse relationship to asset feature
    features = relationship(
        'AssetFeature', 
        back_populates='asset',
        cascade="all, delete-orphan", # cascade from Asset to AssetFeature
        lazy="selectin",  # Ensures relationship loads in async contexts

    )

    # Reverse relationship to the AssetCloudImage
    cloud_images = relationship(
        'AssetCloudImage', 
        back_populates='asset',
        cascade="all, delete-orphan", # cascade from Asset to AssetCloudImage
        lazy="selectin",  # Ensures relationship loads in async contexts

    )


class AssetFeature(Base):
    __tablename__ = 'asset_features'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)

    # Foreign key relationship to Asset (cascade on delete)
    asset_id = Column(
        Integer, 
        ForeignKey(
            'assets.id', 
            name='fk_asset_features_asset_id', 
            use_alter=True,
            ondelete='CASCADE'
        )
    )
    asset = relationship(
        'Asset', 
        back_populates='features',
        foreign_keys=[asset_id],
        lazy="selectin",  # Ensures relationship loads in async contexts

    )

    # Reverse relationship to the AssetCloudImage
    cloud_images = relationship(
        'AssetCloudImage', 
        back_populates='asset_feature',
        cascade="all, delete-orphan", # cascade from AssetFeature to AssetCloudImage
        lazy="selectin",  # Ensures relationship loads in async contexts
    )


class AssetCloudImage(AbstractCloudImage):
    __tablename__ = 'asset_cloud_images'

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key relationship to asset (no cascade)
    asset_id = Column(
        Integer, 
        ForeignKey(
            'assets.id', 
            name='fk_asset_cloud_images_asset_id', 
            use_alter=True,
            ondelete='CASCADE'
        )
    )
    asset = relationship(
        'Asset', 
        back_populates='cloud_images',
        foreign_keys=[asset_id],
        lazy="selectin",  # Ensures relationship loads in async contexts

    )

    # Foreign key relationship to asset_features (no cascade)
    asset_feature_id = Column(
        Integer, 
        ForeignKey(
            'asset_features.id', 
            name='fk_asset_cloud_images_asset_feature_id', 
            use_alter=True,
            ondelete='CASCADE'
        )
    )
    asset_feature = relationship(
        'AssetFeature', 
        back_populates='cloud_images',
        foreign_keys=[asset_feature_id],
        lazy="selectin",  # Ensures relationship loads in async contexts

    )



@event.listens_for(User, 'before_insert')
@event.listens_for(Asset, 'before_insert')
@event.listens_for(AbstractCloudImage, 'before_insert')
# Listen for the 'before_insert' event to set updated_at
def set_updated_at_before_insert(mapper, connection, target):
    target.updated_at = func.now()