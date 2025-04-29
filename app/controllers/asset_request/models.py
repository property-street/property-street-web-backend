from sqlalchemy import (
    Column,
    Integer,
    ForeignKey,
    Text,
    Table,
    DateTime,
    func,
    event
)
from sqlalchemy.orm import relationship


from property_street_backend.config.postgres_connection_manager import Base

request_agent_association = Table(
    'request_agent_association',
    Base.metadata,
    Column(
        'request_id',
        Integer,
        ForeignKey(
            'asset_requests.id',
            name = 'fk_request_agent_association_asset_requests',
            ondelete='CASCADE'
        ),
        primary_key = True
    ),
    Column(
        'agent_id',
        Integer,
        ForeignKey(
            'agents.id',
            name = 'fk_request_agent_association_agents',
            ondelete = 'CASCADE'
        ),
        primary_key=True
    )
)

request_asset_association = Table(
    'request_asset_association',
    Base.metadata,
    Column(
        'request_id',
        Integer,
        ForeignKey(
            'asset_requests.id',
            name = 'fk_request_agent_association_asset_requests',
            ondelete='CASCADE'
        ),
        primary_key = True
    ),
    Column(
        'asset_id',
        Integer,
        ForeignKey(
            'assets.id',
            name = 'fk_request_agent_association_assets',
            ondelete = 'CASCADE'
        ),
        primary_key=True
    )
)

class AssetRequest(Base):
    __tablename__ = "asset_requests"

    id = Column(Integer, primary_key=True, index=True)
    description = Column(Text, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # relationship to requester 
    requester_id = Column(
        Integer,
        ForeignKey(
            'users.id',
            name='fk_asset_requests_users',
            ondelete='CASCADE'
        ),
        nullable = False
    )
    requester = relationship(
        'User',
        back_populates = 'requested_assets',
        uselist = False, # many to one relationship
        lazy = 'selectin'
    )

    # many to many relationship to agents
    resolvers = relationship(
        'Agent',
        secondary='request_agent_association',
        lazy='selectin',
        back_populates = 'resolved_asset_requests'
    )

    # many to many relationsip to assets
    assets = relationship(
        'Asset',
        secondary = 'request_asset_association',
        lazy='selectin',
        back_populates='requests'
    )

    # relationship to area
    area_id = Column(
        Integer,
        ForeignKey(
            'areas.id',
            name='fk_asset_requests_areas',
            ondelete='RESTRICT'
        ),
        nullable=False
    )
    area = relationship(
        'Area',
        back_populates='requested_asset',
        uselist=False,
        lazy='selectin'
    )


@event.listens_for(AssetRequest, 'before_insert')
def set_updated_at_before_insert(mapper, connection, target):
    target.updated_at = func.now()