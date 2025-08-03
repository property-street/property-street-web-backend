"""Modification of Agent Model to abstract type, removal of relationship to an Agent model and reference to a User model

Revision ID: 0acaa2bdc1e9
Revises: 81d45c138470
Create Date: 2025-08-03 05:43:17.867973

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0acaa2bdc1e9'
down_revision: Union[str, None] = '81d45c138470'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop all foreign key constraints pointing to agents first
    op.drop_constraint('fk_assets_agent_id', 'assets', type_='foreignkey')
    op.drop_constraint('fk_ratings_agents', 'ratings', type_='foreignkey')
    op.drop_constraint('fk_request_agent_association_agents', 'request_agent_association', type_='foreignkey')
    op.drop_constraint('fk_users_agent_profile_id', 'users', type_='foreignkey')

    # Then drop related constraints that depend on agents table
    op.drop_constraint('users_agent_profile_id_key', 'users', type_='unique')

    # Now drop the agents table safely
    op.drop_index('ix_agents_id', table_name='agents')
    op.drop_table('agents')

    # Now create new relationships with users table
    op.create_foreign_key('fk_assets_agent_id_users', 'assets', 'users', ['agent_id'], ['id'], ondelete='CASCADE')
    op.add_column('ratings', sa.Column('rater_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_ratings_rater_id_users', 'ratings', 'users', ['rater_id'], ['id'], ondelete='CASCADE', use_alter=True)
    op.create_foreign_key('fk_ratings_agent_id_users', 'ratings', 'users', ['agent_id'], ['id'], ondelete='CASCADE', use_alter=True)
    op.create_foreign_key('fk_request_agent_association_agents', 'request_agent_association', 'users', ['agent_id'], ['id'], ondelete='CASCADE')

    # Add ratings metadata directly to user
    op.add_column('users', sa.Column('total_ratings', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('total_stars', sa.Integer(), nullable=True))

    # Remove obsolete columns
    op.drop_column('users', 'agent_profile_id')
    op.drop_column('users', 'rating_id')



def downgrade() -> None:
    # Drop new FKs that point to 'users'
    op.drop_constraint('fk_assets_agent_id_users', 'assets', type_='foreignkey')
    op.drop_constraint('fk_ratings_agent_id_users', 'ratings', type_='foreignkey')
    op.drop_constraint('fk_ratings_rater_id_users', 'ratings', type_='foreignkey')
    op.drop_constraint('fk_request_agent_association_agents', 'request_agent_association', type_='foreignkey')

    # Drop new columns
    op.drop_column('ratings', 'rater_id')
    op.drop_column('users', 'total_stars')
    op.drop_column('users', 'total_ratings')

    # Restore 'agent_profile_id' and 'rating_id' to 'users'
    op.add_column('users', sa.Column('rating_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('users', sa.Column('agent_profile_id', sa.INTEGER(), autoincrement=False, nullable=True))

    # Recreate 'agents' table
    op.create_table(
        'agents',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('total_ratings', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('total_stars', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint('id', name='agents_pkey')
    )

    # Restore index
    op.create_index('ix_agents_id', 'agents', ['id'], unique=False)

    # Restore old FKs
    op.create_foreign_key('fk_assets_agent_id', 'assets', 'agents', ['agent_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_ratings_agents', 'ratings', 'agents', ['agent_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_request_agent_association_agents', 'request_agent_association', 'agents', ['agent_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_users_agent_profile_id', 'users', 'agents', ['agent_profile_id'], ['id'], ondelete='SET NULL')
    op.create_unique_constraint('users_agent_profile_id_key', 'users', ['agent_profile_id'])
    op.create_foreign_key('fk_users_ratings', 'users', 'ratings', ['rating_id'], ['id'], ondelete='CASCADE')
