"""Add IANA timezone names while retaining legacy offsets.

Revision ID: 20261104_0002
Revises: 20260309_0001
"""

from alembic import op
import sqlalchemy as sa

revision = "20261104_0002"
down_revision = "20260309_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "attendance_settings",
        sa.Column("timezone_name", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("attendance_settings", "timezone_name")
