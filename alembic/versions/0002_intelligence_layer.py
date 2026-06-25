"""intelligence layer schema

Revision ID: 0002_intelligence_layer
Revises: 0001_initial
Create Date: 2026-06-25
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_intelligence_layer"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("repositories", sa.Column("overview", sa.JSON(), nullable=True))
    op.add_column("repositories", sa.Column("dependency_analysis", sa.JSON(), nullable=True))
    op.add_column("repositories", sa.Column("architecture_summary", sa.Text(), nullable=True))
    op.add_column("repositories", sa.Column("complexity", sa.String(length=32), nullable=True))
    op.add_column("repositories", sa.Column("learning_difficulty", sa.String(length=32), nullable=True))

    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index(op.f("ix_chat_sessions_repository_id"), "chat_sessions", ["repository_id"], unique=False)
    op.create_index(op.f("ix_chat_sessions_user_id"), "chat_sessions", ["user_id"], unique=False)

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("chat_session_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["chat_session_id"], ["chat_sessions.id"]),
    )
    op.create_index(op.f("ix_chat_messages_chat_session_id"), "chat_messages", ["chat_session_id"], unique=False)
    op.create_index(op.f("ix_chat_messages_role"), "chat_messages", ["role"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_chat_messages_role"), table_name="chat_messages")
    op.drop_index(op.f("ix_chat_messages_chat_session_id"), table_name="chat_messages")
    op.drop_table("chat_messages")

    op.drop_index(op.f("ix_chat_sessions_user_id"), table_name="chat_sessions")
    op.drop_index(op.f("ix_chat_sessions_repository_id"), table_name="chat_sessions")
    op.drop_table("chat_sessions")

    op.drop_column("repositories", "learning_difficulty")
    op.drop_column("repositories", "complexity")
    op.drop_column("repositories", "architecture_summary")
    op.drop_column("repositories", "dependency_analysis")
    op.drop_column("repositories", "overview")
