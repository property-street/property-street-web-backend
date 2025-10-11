from sqlalchemy import (
    Column, 
    Integer, 
    String,
    ForeignKey, 
    func,
    Table,
    Float,
    DateTime,
    Enum as SQLAlchemyEnum,
)
from pydantic import ValidationError
from sqlalchemy.orm import relationship, validates
from sqlalchemy.dialects.postgresql import JSONB

from .schemas import FMTMSG
from .enums import MessageStatus, MessageTypes
from property_street_backend.config.postgres_connection_manager import Base

# message-thread Association Table for many-to-many relationship
thread_chat_session_association = Table(
    'thread_chat_session_association',
    Base.metadata,
    Column(
        'thread_id', 
        Integer, 
        ForeignKey(
            'threads.id', 
            name='fk_thread_chat_session_association_thread_id',
            ondelete='RESTRICT'
        ), 
        primary_key=True
    ),
    Column(
        'chat_session_id', 
        Integer, 
        ForeignKey(
            'chat_sessions.id', 
            name='fk_thread_chat_session_association_chat_session_id',
            ondelete='RESTRICT'
        ), 
        primary_key=True
    )
)
# message-thread Association Table for many-to-many relationship
threads_participants_association = Table(
    'threads_participants_association',
    Base.metadata,
    Column(
        'thread_id', 
        Integer, 
        ForeignKey(
            'threads.id', 
            name='fk_threads_participants_association_thread_id',
            ondelete='CASCADE'
        ), 
        primary_key=True
    ),
    Column(
        'user_id', 
        Integer, 
        ForeignKey(
            'users.id', 
            name='fk_threads_participants_association_user_id',
            ondelete='RESTRICT'
        ), 
        primary_key=True
    )
)


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign key relationship to User
    user_id = Column(
        Integer, 
        ForeignKey(
            'users.id', 
            name='fk_chat_sessions_user_id', 
            ondelete='CASCADE'
        )
    )
    user = relationship(
        'User', 
        back_populates='chat_session',
        lazy="selectin",  # Ensures relationship loads in async contexts
        uselist=False, # many to one relationship, restricts it to associating with only one User instance.
    )

    # relationship to threads
    threads = relationship(
        'Thread',
        secondary='thread_chat_session_association',
        back_populates='chat_sessions',
        lazy='selectin', # Ensures relationship loads in async contexts
    )


class Thread(Base):
    __tablename__ = "threads"
    
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # relationship with messages
    messages = relationship(
        'Message', 
        back_populates='thread',
        lazy="selectin",  # Ensures relationship loads in async contexts
    )

    # Many-to-many relationship to chat_session
    chat_sessions = relationship(
        'ChatSession',
        secondary='thread_chat_session_association',
        back_populates='threads',
        lazy='selectin', # Ensures relationship loads in async contexts
    )

    # Many to many relationship to User
    participants = relationship(
        'User',
        secondary='threads_participants_association',
        back_populates='threads',
        lazy='selectin'
    )


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    fmt_msg = Column(JSONB, nullable=True)
    msg_type = Column(
        SQLAlchemyEnum(
            MessageTypes, name='message_types',
        ), 
        nullable=True,
        default=MessageTypes.outbound_message
    )
    status = Column(
        SQLAlchemyEnum(
            MessageStatus, name='message_status',
        ), 
        nullable=False,
        default=MessageStatus.unsent
    )
    server_timestamp_ms = Column(Float, nullable=False)
    updated_timestamp_ms = Column(Float)

    # Foreign key relationship to Thread
    thread_id = Column(
        Integer, 
        ForeignKey(
            'threads.id', 
            name='fk_messages_thread_id', 
            ondelete='CASCADE'
        )
    )
    thread = relationship(
        'Thread',
        back_populates='messages',
        lazy='selectin'
    )

    # Foreign key relationship to sender
    sender_id = Column(
        Integer, 
        ForeignKey(
            'users.id', 
            name='fk_messages_sender_id', 
            ondelete='CASCADE'
        )
    )
    sender = relationship(
        'User',
        foreign_keys=[sender_id],
        back_populates='sent_messages',
        lazy='selectin'
    )

    # Foreign key relationship to recipient
    recipient_id = Column(
        Integer, 
        ForeignKey(
            'users.id', 
            name='fk_messages_recipient_id', 
            ondelete='CASCADE'
        )
    )
    recipient = relationship(
        'User',
        foreign_keys=[recipient_id],
        back_populates='received_messages',
        lazy='selectin'
    )

    @validates("fmt_msg")
    def validate_fmt_msg(self, key, value):
        if value is None:
            return None
        
        # Allow Pydantic model instance
        if isinstance(value, FMTMSG):
            return value.model_dump()
        
        # Validate dict input
        try:
            validated = FMTMSG(**value)
        except ValidationError as e:
            raise ValueError(f"Invalid fmt_msg format: {e}")
        
        return validated.model_dump()