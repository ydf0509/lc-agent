"""add http_traces to chat_ui_messages

Revision ID: 20260623_http_traces
Revises: a342dc61a740
Create Date: 2026-06-23 00:10:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260623_http_traces"
down_revision: Union[str, Sequence[str], None] = "a342dc61a740"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("chat_ui_messages", schema=None) as batch_op:
        batch_op.add_column(sa.Column("http_traces", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("chat_ui_messages", schema=None) as batch_op:
        batch_op.drop_column("http_traces")
