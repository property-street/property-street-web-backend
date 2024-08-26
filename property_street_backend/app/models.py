from sqlalchemy import (
    Column, 
    Integer, 
    String,
    ForeignKey, 
    Date, 
    Boolean, 
    JSON, 
    Text, 
    DateTime,
    Enum as SQLAlchemyEnum, 
    event,
    func 
)
from sqlalchemy.future import select
from sqlalchemy import types as _types
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.enums import EmailManagementReasonChoice
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
    

# Enum for reason choices


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

        # Listen for the 'before_insert' event to set updated_at
    
#@event.listens_for(EmailManagementModel, 'before_insert')
#def set_updated_at_before_insert(mapper, connection, target):
#    target.updated_at = func.now()