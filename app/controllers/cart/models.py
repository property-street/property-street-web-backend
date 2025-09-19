from sqlalchemy import Column, ForeignKey, Integer, DateTime, func, CheckConstraint, event, func
from sqlalchemy.orm import relationship
from property_street_backend.config.postgres_connection_manager import Base

class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True)
    quantity = Column(Integer, default=1)
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    
    # asset Relationships
    asset_id = Column(
        Integer, 
        ForeignKey(
            "assets.id",
            name="fk_cart_items_assets",
            ondelete="CASCADE"
        ),
        nullable=False
    )
    asset = relationship(
        "Asset", 
        back_populates="cart_items",
        lazy="selectin",
        uselist=False
    )

    __table_args__ = (
        CheckConstraint("quantity <= 1", name="check_quantity_max"),
    )

@event.listens_for(CartItem, 'before_insert')
# Listen for the 'before_insert' event to set updated_at
def set_updated_at_before_insert(mapper, connection, target):
    target.updated_at = func.now()