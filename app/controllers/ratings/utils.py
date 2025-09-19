from sqlalchemy import Column, Integer
from sqlalchemy.ext.declarative import declared_attr

from property_street_backend.config.postgres_connection_manager import Base


class AggregateRatingAClass(Base):
    __abstract__ = True # Ensure this class is not mapped to its own table

    total_ratings = Column(Integer, default=0)
    total_stars = Column(Integer, default=0)

    # Optionally, if you want dynamic table names, you can define a declared_attr:
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()  # Use class name as table name