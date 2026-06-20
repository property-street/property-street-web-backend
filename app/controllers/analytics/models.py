from sqlalchemy import (
    Column, 
    BigInteger,
    Enum as SQLAlchemyEnum,
    Date
)

from .enums import ResourceType
from sqlalchemy.orm import validates
from pydantic import ValidationError
from sqlalchemy.dialects.postgresql import JSONB
from .schemas import UsersAExtra, PropertiesAExtra
from property_street_backend.config.postgres_connection_manager import Base


class PlatformMetric(Base):
    __tablename__ = "platform_metrics"

    resource_type = Column(
        SQLAlchemyEnum(ResourceType),
        primary_key=True
    )

    created_today = Column(BigInteger, default=0)
    created_this_week = Column(BigInteger, default=0)
    created_this_month = Column(BigInteger, default=0)

    total = Column(BigInteger, default=0)

    reported = Column(BigInteger, default=0)
    deleted = Column(BigInteger, default=0)

    active = Column(BigInteger, default=0)
    inactive = Column(BigInteger, default=0)
    suspended = Column(BigInteger, default=0)

    last_day_reset = Column(Date)
    last_week_reset = Column(Date)
    last_month_reset = Column(Date)

    extra = Column(JSONB, default=dict)

    def __init__(self, **kwargs):
        # Store family during init
        self._resource_type = kwargs.get('resource_type')
        super().__init__(**kwargs)
        
    @validates("extra")
    def validate_extra(self, key, value):
        if value is None:
            raise ValueError(f"Invalid extra value")
        
        ExtraSchema = None
        resource_type = self.resource_type or getattr(self, '_resource_type', None)
        match resource_type:
            case ResourceType.property:
                ExtraSchema = PropertiesAExtra
            case ResourceType.user:
                ExtraSchema = UsersAExtra
            case ResourceType.user:
                ExtraSchema = UsersAExtra
            case _:
                return value
        
        # Allow Pydantic model instance
        if isinstance(value, ExtraSchema):
            return value.model_dump()
        
        # Validate dict input
        try:
            validated = ExtraSchema(**value)
        except ValidationError as e:
            raise ValueError(f"Invalid extra format: {e}")
        
        return validated.model_dump()