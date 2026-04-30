"""Add token management and activity logs

Revision ID: a8f4d2b9c731
Revises: 6cef8427174c
Create Date: 2026-04-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a8f4d2b9c731"
down_revision: Union[str, None] = "6cef8427174c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    activity_status_choice = sa.Enum(
        "success",
        "failed",
        "pending",
        "error",
        name="activity_status_choice",
    )
    activity_status_choice.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "refresh_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("access_token_hash", sa.String(), nullable=True),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_agent", sa.String(), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_revoked", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_refresh_sessions_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_refresh_sessions_id"), "refresh_sessions", ["id"], unique=False)
    op.create_index(op.f("ix_refresh_sessions_user_id"), "refresh_sessions", ["user_id"], unique=False)

    op.create_table(
        "request_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("refresh_session_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("method", sa.String(), nullable=False),
        sa.Column("endpoint", sa.String(), nullable=False),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("user_agent", sa.String(), nullable=True),
        sa.Column("response_status_code", sa.Integer(), nullable=False),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["refresh_session_id"],
            ["refresh_sessions.id"],
            name="fk_request_logs_refresh_session_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_request_logs_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_request_logs_id"), "request_logs", ["id"], unique=False)
    op.create_index(op.f("ix_request_logs_refresh_session_id"), "request_logs", ["refresh_session_id"], unique=False)
    op.create_index(op.f("ix_request_logs_user_id"), "request_logs", ["user_id"], unique=False)

    op.create_table(
        "activity_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=255), nullable=False),
        sa.Column("status", activity_status_choice, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("method", sa.String(length=10), nullable=True),
        sa.Column("endpoint", sa.String(length=500), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("request_body", sa.Text(), nullable=True),
        sa.Column("response_status_code", sa.Integer(), nullable=True),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("activity_type", sa.String(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_activity_logs_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_activity_logs_action"), "activity_logs", ["action"], unique=False)
    op.create_index(op.f("ix_activity_logs_id"), "activity_logs", ["id"], unique=False)
    op.create_index(op.f("ix_activity_logs_status"), "activity_logs", ["status"], unique=False)
    op.create_index(op.f("ix_activity_logs_timestamp"), "activity_logs", ["timestamp"], unique=False)
    op.create_index(op.f("ix_activity_logs_user_id"), "activity_logs", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_activity_logs_user_id"), table_name="activity_logs")
    op.drop_index(op.f("ix_activity_logs_timestamp"), table_name="activity_logs")
    op.drop_index(op.f("ix_activity_logs_status"), table_name="activity_logs")
    op.drop_index(op.f("ix_activity_logs_id"), table_name="activity_logs")
    op.drop_index(op.f("ix_activity_logs_action"), table_name="activity_logs")
    op.drop_table("activity_logs")

    op.drop_index(op.f("ix_request_logs_user_id"), table_name="request_logs")
    op.drop_index(op.f("ix_request_logs_refresh_session_id"), table_name="request_logs")
    op.drop_index(op.f("ix_request_logs_id"), table_name="request_logs")
    op.drop_table("request_logs")

    op.drop_index(op.f("ix_refresh_sessions_user_id"), table_name="refresh_sessions")
    op.drop_index(op.f("ix_refresh_sessions_id"), table_name="refresh_sessions")
    op.drop_table("refresh_sessions")

    sa.Enum(name="activity_status_choice").drop(op.get_bind(), checkfirst=True)
