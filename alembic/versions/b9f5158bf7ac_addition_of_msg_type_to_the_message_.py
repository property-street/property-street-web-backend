"""addition of msg_type to the Message model

Revision ID: b9f5158bf7ac
Revises: 0acaa2bdc1e9
Create Date: 2025-08-05 11:52:21.212214

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b9f5158bf7ac'
down_revision: Union[str, None] = '0acaa2bdc1e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Define the enum type
message_types = sa.Enum(
    'inbound_message',
    'outbound_message',
    'delivered_message',
    'read_message',
    'completed',
    name='message_types'
)

def upgrade() -> None:
    # Create the enum type in the DB
    message_types.create(op.get_bind())

    # Then add the column using the enum
    op.add_column('messages', sa.Column('msg_type', message_types, nullable=True))

    # Drop the old foreign key and column (if still needed)
    op.drop_constraint('fk_cart_items_user', 'cart_items', type_='foreignkey')
    op.drop_column('cart_items', 'user_id')


def downgrade() -> None:
    # Revert the changes in reverse order
    op.add_column('cart_items', sa.Column('user_id', sa.INTEGER(), nullable=False))
    op.create_foreign_key('fk_cart_items_user', 'cart_items', 'users', ['user_id'], ['id'], ondelete='CASCADE')

    op.drop_column('messages', 'msg_type')

    # Drop the enum type from the DB
    message_types.drop(op.get_bind())