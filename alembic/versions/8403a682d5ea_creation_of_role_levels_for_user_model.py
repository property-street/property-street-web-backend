"""Creation of role levels for user model
Alter of availability field of assets
Creation of gender field of users
Deletion of client_type of users

Revision ID: 8403a682d5ea
Revises: 592ada0e7370
Create Date: 2025-07-02 17:13:23.819199

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8403a682d5ea'
down_revision: Union[str, None] = '592ada0e7370'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Define the enums separately
availability_enum = postgresql.ENUM(
    'available', 'unavailable', 'reserved', 'pending', 'sold', 'rented', 'maintenance',
    name='asset_availability_status'
)

gender_enum = postgresql.ENUM(
    'male', 'female', 'custom',
    name='client_gender_choice'
)

user_role_enum = postgresql.ENUM(
    'admin', 'staff', 'agent', 'user',
    name='user_role_choice'
)

def upgrade() -> None:
    # Create the enum types first
    availability_enum.create(op.get_bind())
    gender_enum.create(op.get_bind())
    user_role_enum.create(op.get_bind())

    # Now alter the column to use the new enum
    op.alter_column(
        'assets',
        'availability',
        existing_type=sa.TEXT(),
        type_=availability_enum,
        postgresql_using="availability::asset_availability_status",
        existing_nullable=False
    )

    op.add_column('users', sa.Column('gender', gender_enum, nullable=True))
    op.add_column(
        'users',
        sa.Column('user_role', user_role_enum, nullable=False, server_default='user')
    )
    op.alter_column('users', 'user_role', server_default=None)
    op.drop_column('users', 'client_type')



def downgrade() -> None:
    # Re-add the dropped 'client_type' column
    client_type_enum = postgresql.ENUM('client', 'agent', name='client_type_choice')
    client_type_enum.create(op.get_bind())
    op.add_column(
        'users',
        sa.Column('client_type', client_type_enum, nullable=True)
    )

    # Drop newly added columns
    op.drop_column('users', 'user_role')
    op.drop_column('users', 'gender')

    # Revert availability column back to TEXT
    op.alter_column(
        'assets',
        'availability',
        existing_type=postgresql.ENUM(
            'available', 'unavailable', 'reserved', 'pending', 'sold', 'rented', 'maintenance',
            name='asset_availability_status'
        ),
        type_=sa.TEXT(),
        postgresql_using="availability::text",
        existing_nullable=False
    )

    # Drop the enums
    user_role_enum.drop(op.get_bind())
    gender_enum.drop(op.get_bind())
    availability_enum.drop(op.get_bind())
    # client_type_enum.drop(op.get_bind())