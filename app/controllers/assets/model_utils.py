from sqlalchemy import (
    Column,
    Integer,
    Boolean, 
    ForeignKey,
)
from sqlalchemy.orm import relationship, declared_attr

from property_street_backend.config.postgres_connection_manager import Base

class UserStatsPerAssetAbsCls(Base):
    __abstract__ = True

    # id = Column(Integer, primary_key=True, index=True)
    liked = Column(Boolean, default=False)
    saved = Column(Boolean, default=False)
    cart = Column(Boolean, default=False)
    share_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    click_count = Column(Integer, default=0)
    contact_count = Column(Integer, default=0)


class UserStatsPerProperty(UserStatsPerAssetAbsCls):
    __tablename__ = "user_stats_per_property"

    id = Column(Integer, primary_key=True, index=True)

    asset_id  = Column(
        Integer,
        ForeignKey("assets.id", name="fk_stats_asset_id_assets", ondelete="CASCADE"),
        nullable=False
    )
    asset = relationship(
        "Asset", lazy="selectin", uselist=False
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", name="fk_stats_user_id_users", ondelete="CASCADE"),
        nullable=False,
    )
    user = relationship(
        "User", lazy='selectin', uselist=False, back_populates="user_per_property_stats"
    )


class UserAssetAbsCls(Base):
    __abstract__ = True

    @declared_attr
    def user_per_property_stats(cls): 
        return relationship(
            "UserStatsPerProperty", lazy="selectin", back_populates="user"
        )