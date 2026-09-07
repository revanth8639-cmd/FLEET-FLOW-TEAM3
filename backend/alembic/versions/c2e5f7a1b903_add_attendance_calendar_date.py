"""Add the canonical calendar date to attendance records."""

from alembic import op
import sqlalchemy as sa


revision = "c2e5f7a1b903"
down_revision = "b8c9d0e1f234"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("attendance", sa.Column("date", sa.Date(), nullable=True))
    op.execute("UPDATE attendance SET date = check_in::date WHERE date IS NULL")
    op.execute("UPDATE attendance SET date = CURRENT_DATE WHERE date IS NULL")
    op.alter_column("attendance", "date", nullable=False)


def downgrade() -> None:
    op.drop_column("attendance", "date")
