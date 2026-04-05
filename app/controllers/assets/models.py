from sqlalchemy import (
    Text,
    func,
    event,
    event,
    String,
    Column,
    Integer,
    Numeric,
    Boolean,
    DateTime,
    ForeignKey,
    BigInteger,
    Enum as SqlalchemyEnum,
)
from sqlalchemy.future import select
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

from .enums import InteractionType as IntentFactor
from property_street_backend.config.settings import (
    BETA_LAUNCHING, 
    BETA_LAUNCH_PROPERTY_LIMIT,
    UNLIMITED_BETA_AGENTS_EMAILS
)
from property_street_backend.app.controllers.actors.models import User
from property_street_backend.app.models_helper import AbstractCloudImage
from property_street_backend.config.postgres_connection_manager import Base
from property_street_backend.app.controllers.ratings.utils import AggregateRatingAClass


class Asset(AggregateRatingAClass):
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
        ),
        nullable=False,
    )
    area = relationship(
        'Area',
        back_populates='asset',
        lazy='selectin',
        uselist = False
    )

    currency = Column(String, nullable=False)
    status = Column(String, nullable=False, default = 'available',)
    price = Column(Numeric(15, 2), nullable=False)  # Up to 10 digits, 2 decimal places; returns a Decimal type
    lease_duration = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    listing_type=Column(String, nullable=False)

    # verification
    verified = Column(Boolean, nullable=False, default=False)
    datetime_declined = Column(DateTime(timezone=True))
    datetime_verified = Column(DateTime(timezone=True))

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
            'users.id', 
            name='fk_assets_agent_id_users', 
            ondelete='CASCADE'
        ),
        nullable=False
    )
    agent = relationship(
        'User', 
        backref='assets',
        lazy="selectin",  # Ensures relationship loads in async contexts
        uselist=False
    )

    # One-to-one relationship for cover image (no cascade)
    cover_image_id = Column(
        Integer, 
        ForeignKey(
            'cloud_image_details.id', 
            name='fk_assets_cover_image_id', 
            use_alter=True, 
            ondelete='CASCADE'
        ), 
        nullable=True
    )
    cover_image = relationship(
        'CloudImageDetail',
        back_populates='asset',
        uselist=False,
        foreign_keys=[cover_image_id],
        post_update=True,
        lazy="selectin",
        cascade="all, delete-orphan", # Ensures that if the parent disappears, the child is deleted.
        single_parent=True # Required for delete-orphan behavior in one-to-one relationships.
    )
    
    # Many-to-many relationship with Tag
    tags = relationship(
        'Tag', 
        secondary='asset_tag_association', 
        back_populates='assets',
        lazy="selectin",  # Ensures relationship loads in async contexts
        uselist=True,
    )

    # Reverse relationship to asset feature
    features = relationship(
        'AssetFeature', 
        back_populates='asset',
        cascade="all, delete-orphan", # cascade from Asset to AssetFeature
        lazy="selectin",  # Ensures relationship loads in async contexts
        uselist = True,
    )

    # Reverse relationship to the AssetCloudImage
    unfeatured_images = relationship(
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

    likes = Column(Integer, default=0)
    saves = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    views = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    contacts = Column(Integer, default=0)
    carts = Column(Integer, default=0)

    _user_stats = None

    @hybrid_property
    def user_stats(self):
        return self._user_stats
    @user_stats.setter
    def user_stats(self, value):
        self._user_stats = value

@event.listens_for(Asset, 'before_insert')
def validate_agent_and_check_beta_limit(mapper, connection, target):
    """
    Listener to validate agent and enforce beta mode asset limits.
    
    Validates:
        1. Agent exists and has proper authorization
        2. Beta mode agents don't exceed 5 assets
    
    Raises:
        ValueError: If agent is invalid or beta user exceeds 5 assets
    """
    # Timestamp
    target.updated_at = func.now()

    # --- Validate agent_id exists ---
    if not target.agent_id:
        raise ValueError("Property must be assigned to an agent.")

    # --- Fetch agent data (SCALAR, SAFE) ---
    agent_row = connection.execute(
        select(
            User.id,
            User.username,
            User.user_role,
            User.email,
        ).where(User.id == target.agent_id)
    ).one_or_none()

    if not agent_row:
        raise ValueError(f"No agent found with ID {target.agent_id}.")

    agent_id, username, role, email = agent_row

    # --- Validate role ---
    if role not in ("staff", "agent", "admin"):
        raise ValueError(
            f"Unauthorized asset creation: user '{username}' has role '{role}'."
        )

    # --- Beta mode enforcement ---
    if BETA_LAUNCHING:
        asset_count = connection.execute(
            select(func.count(Asset.id)).where(Asset.agent_id == agent_id)
        ).scalar_one()

        if asset_count >= BETA_LAUNCH_PROPERTY_LIMIT and email not in UNLIMITED_BETA_AGENTS_EMAILS:
            raise ValueError(
                f"Beta mode agent '{username}' has reached the 5-asset limit."
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
        post_update=True,
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
        back_populates='unfeatured_images',
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



class EventBase(Base):
    __abstract__ = True  # ← Important

    id = Column(Integer, primary_key=True, index=True)
    timestamp_ms = Column(BigInteger)


class InteractionEventAbsCls(EventBase):
    __abstract__ = True  # ← Important
    # For analytical purposes
    user_id = Column(
        Integer, 
        ForeignKey(
            "users.id",
            name="fk_intent_events_user_id",
            ondelete="CASCADE"
        ), index=True, nullable=False
    )

    factor = Column(
        SqlalchemyEnum(IntentFactor, name="intent_factor"),
        nullable=False, index=True,
    )


class PropertyInteractionEvent(InteractionEventAbsCls):
    __tablename__ = "property_interaction_event"
    
    property_id = Column(
        Integer,
        ForeignKey(
            "assets.id",
            name="fk_property_interaction_event_asset_id",
            ondelete="CASCADE"
        ),
        index=True, nullable=False
    )