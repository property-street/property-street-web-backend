"""change of Message model status field to enums

Revision ID: 40de413421e4
Revises: e73688d0d0e8
Create Date: 2025-07-20 00:11:04.692517

"""
from typing import Sequence, Union
from sqlalchemy.dialects import postgresql
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '40de413421e4'
down_revision: Union[str, None] = 'e73688d0d0e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Define the ENUM type
message_status_enum = postgresql.ENUM(
    'unsent', 'sent', 'delivered', 'read',
    name='message_status'
)


def upgrade() -> None:
    # Create ENUM type before using it
    message_status_enum.create(op.get_bind())

    # Alter the column to use ENUM type
    op.alter_column(
        'messages', 
        'status',
        existing_type=sa.VARCHAR(),
        type_=message_status_enum,
        postgresql_using="status::message_status",
        existing_nullable=False
    )


def downgrade() -> None:
    # Revert column back to VARCHAR
    op.alter_column(
        'messages', 
        'status',
        existing_type=message_status_enum,
        type_=sa.VARCHAR(),
        postgresql_using="status::text",
        existing_nullable=False
    )

    # Drop ENUM type
    message_status_enum.drop(op.get_bind())