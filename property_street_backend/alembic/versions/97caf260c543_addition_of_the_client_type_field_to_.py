"""Addition of the client_type field to the User model

Revision ID: 97caf260c543
Revises: bb88cc489237
Create Date: 2024-08-29 13:56:41.506044

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '97caf260c543'
down_revision: Union[str, None] = 'bb88cc489237'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the enum type first
    client_type_enum = sa.Enum('client', 'agent', name='client_type_choice')
    client_type_enum.create(op.get_bind())  # Bind to the current connection and create the enum

    # Now add the column with the enum type
    op.add_column('users', sa.Column('client_type', client_type_enum, nullable=True))


def downgrade() -> None:
    # Drop the column first
    op.drop_column('users', 'client_type')

    # Then drop the enum type
    client_type_enum = sa.Enum('client', 'agent', name='client_type_choice')
    client_type_enum.drop(op.get_bind())
