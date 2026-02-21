from sqlalchemy import (
    Column,
    Integer,
    Boolean, 
    ForeignKey,
)
from sqlalchemy.orm import relationship

from property_street_backend.config.postgres_connection_manager import Base

class UserPerAssetStatsAbsCls(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)
    liked = Column(Boolean, default=False)
    saved = Column(Boolean, default=False)
    cart = Column(Boolean, default=False)
    share_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)


class UserPerPropertyStats(UserPerAssetStatsAbsCls):
    __tablename__ = "user_per_property_stats"

    id = Column(Integer, primary_key=True, index=True)
    liked = Column(Boolean, default=False)
    saved = Column(Boolean, default=False)
    cart = Column(Boolean, default=False)
    share_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)

    asset_id  = Column(
        Integer,
        ForeignKey("assets.id", name="fk_stats_asset_id_assets", ondelete="CASCADE"),
        nullable=False
    )
    asset = relationship(
        "Asset", lazy="selectin", useList=False
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

    user_per_property_stats = relationship(
        "UserPerPropertyStats", lazy="seletin", back_populates="user"
    )