"""add can_be_subagent to agent_presets

Revision ID: 20260904_add_can_be_subagent
Revises: 20260904_add_default_delegation
Create Date: 2026-09-04
"""

import sqlalchemy as sa
from alembic import op


revision = "20260904_add_can_be_subagent"
down_revision = "20260904_add_default_delegation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("agent_presets") as batch_op:
        batch_op.add_column(
            sa.Column("can_be_subagent", sa.Boolean(), nullable=False, server_default=sa.false())
        )


def downgrade() -> None:
    with op.batch_alter_table("agent_presets") as batch_op:
        batch_op.drop_column("can_be_subagent")
