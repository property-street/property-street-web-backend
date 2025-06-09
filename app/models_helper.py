from sqlalchemy import (
    Column, 
    Integer,
    String,
    DateTime,
    func,
    event,
)

from sqlalchemy.ext.declarative import declared_attr

from property_street_backend.config.postgres_connection_manager import Base

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


@event.listens_for(AbstractCloudImage, 'before_insert')
# Listen for the 'before_insert' event to set updated_at
def set_updated_at_before_insert(mapper, connection, target):
    target.updated_at = func.now()