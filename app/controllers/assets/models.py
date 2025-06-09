from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    Numeric,
    Text,
    DateTime,
    func,
    event,
    Enum as SqlalchemyEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

from .enums import AvailabilityStatus
from property_street_backend.app.models_helper import AbstractCloudImage
from property_street_backend.config.postgres_connection_manager import Base


class Asset(Base):
    __tablename__ = 'assets'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    
    # area
    area_id = Column(
        Integer,
        ForeignKey(
            'areas.id',
            name = 'fk_assets_areas',
            ondelete = 'CASCADE',
            use_alter = True,
        )
    )
    area = relationship(
        'Area',
        back_populates='asset',
        lazy='selectin',
        uselist = False
    )

    currency = Column(String, nullable=False)
    status = Column(String, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)  # Up to 10 digits, 2 decimal places; returns a Decimal type
    lease_duration = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    availability = Column(
        SqlalchemyEnum(AvailabilityStatus, name='asset_availability_status'),
        default = 'available',
        nullable = False
    )

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

    # relationship to CartItem
    cart_items = relationship(
        'CartItem', 
        back_populates='asset',
        cascade="all, delete-orphan", # cascade from Asset to CartItem
        lazy="selectin",  # Ensures relationship loads in async contexts
    )

    # many-to-many relationship to AssetRequst
    requests = relationship(
        'AssetRequest',
        secondary = 'request_asset_association',
        lazy='selectin',
        back_populates='assets'
    )

    @hybrid_property
    def has_features(self):
        return bool(self.features)  # works in Python

    @has_features.expression
    def has_features(cls):
        return func.count(AssetFeature.id) > 0  # for SQL use, if needed


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


@event.listens_for(Asset, 'before_insert')
# Listen for the 'before_insert' event to set updated_at
def set_updated_at_before_insert(mapper, connection, target):
    target.updated_at = func.now()