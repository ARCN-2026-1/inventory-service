"""create rooms tables

Revision ID: 20260423_000001
Revises:
Create Date: 2026-04-23 00:00:01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260423_000001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rooms",
        sa.Column("room_id", sa.String(length=36), nullable=False),
        sa.Column("room_number", sa.String(length=32), nullable=False),
        sa.Column("room_type", sa.String(length=32), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("price_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("price_currency", sa.String(length=3), nullable=False),
        sa.Column("operational_status", sa.String(length=32), nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("room_id"),
        sa.UniqueConstraint("room_number", name="uq_rooms_room_number"),
    )
    op.create_index("ix_rooms_room_number", "rooms", ["room_number"], unique=True)
    op.create_table(
        "room_availability",
        sa.Column("room_id", sa.String(length=36), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.room_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("room_id"),
    )


def downgrade() -> None:
    op.drop_table("room_availability")
    op.drop_index("ix_rooms_room_number", table_name="rooms")
    op.drop_table("rooms")
