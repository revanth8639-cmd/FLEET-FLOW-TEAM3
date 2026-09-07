"""Ensure one attendance record per driver and calendar date."""

from alembic import op


revision = "e7f1a9c3d205"
down_revision = "d4f6a8b2c190"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint("uq_attendance_driver_date", "attendance", ["driver_id", "date"])


def downgrade() -> None:
    op.drop_constraint("uq_attendance_driver_date", "attendance", type_="unique")
