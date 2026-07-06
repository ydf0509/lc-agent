"""Add sub_agent_runs and sub_agent_events tables

Revision ID: 20260706_add_sub_agent_tables
"""
import sqlalchemy as sa
from alembic import op

revision = "20260706_add_sub_agent_tables"
down_revision = "20260706_add_llm_params"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sub_agent_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("parent_session_id", sa.String(), nullable=False, index=True),
        sa.Column("parent_message_id", sa.String(), nullable=True),
        sa.Column("parent_tool_run_id", sa.String(), nullable=False, index=True),
        sa.Column("parent_agent_id", sa.String(), nullable=False),
        sa.Column("sub_agent_id", sa.String(), nullable=False, index=True),
        sa.Column("sub_agent_name", sa.String(), nullable=False),
        sa.Column("sub_thread_id", sa.String(), nullable=False, index=True),
        sa.Column("task_description", sa.String(), nullable=False, server_default=""),
        sa.Column("status", sa.String(), nullable=False, server_default="running", index=True),
        sa.Column("summary", sa.String(), nullable=False, server_default=""),
        sa.Column("final_result", sa.String(), nullable=False, server_default=""),
        sa.Column("depth", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "sub_agent_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("run_id", sa.String(), nullable=False, index=True),
        sa.Column("event_type", sa.String(), nullable=False, index=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("sub_agent_events")
    op.drop_table("sub_agent_runs")