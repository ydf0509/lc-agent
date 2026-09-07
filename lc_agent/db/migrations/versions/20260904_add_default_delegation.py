"""add default_delegation_description to agent_presets

Revision ID: 20260904_add_default_delegation
Revises: 20260901_add_automation_notifications
Create Date: 2026-09-04
"""

import sqlalchemy as sa
from alembic import op


revision = "20260904_add_default_delegation"
down_revision = "20260901_add_automation_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("agent_presets") as batch_op:
        batch_op.add_column(
            sa.Column("default_delegation_description", sa.String(), nullable=False, server_default="")
        )


def downgrade() -> None:
    with op.batch_alter_table("agent_presets") as batch_op:
        batch_op.drop_column("default_delegation_description")
