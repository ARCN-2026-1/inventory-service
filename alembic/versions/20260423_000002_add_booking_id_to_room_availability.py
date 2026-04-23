"""add booking id to room availability

Revision ID: 20260423_000002
Revises: 20260423_000001
Create Date: 2026-04-23 00:00:02
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260423_000002"
down_revision: str | None = "20260423_000001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "room_availability",
        sa.Column("booking_id", sa.String(length=36), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("room_availability", "booking_id")
