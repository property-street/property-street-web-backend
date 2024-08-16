import enum

from sqlalchemy import Column, Integer, String, ForeignKey, Date, Boolean, JSON, Text, DateTime, Enum as SQLAlchemyEnum, event
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

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
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)