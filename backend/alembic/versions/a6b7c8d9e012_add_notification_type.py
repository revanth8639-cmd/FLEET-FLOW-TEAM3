"""Add notification event type and enforce read defaults."""
from alembic import op
import sqlalchemy as sa


revision = "a6b7c8d9e012"
down_revision = "b7d2f6a9c410"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("notifications", sa.Column("type", sa.String(), nullable=True))
    op.execute("UPDATE notifications SET type = 'info' WHERE type IS NULL")
    op.execute("UPDATE notifications SET is_read = false WHERE is_read IS NULL")
    op.alter_column("notifications", "type", nullable=False, server_default="info")
    op.alter_column("notifications", "is_read", nullable=False, server_default=sa.text("false"))


def downgrade() -> None:
    op.alter_column("notifications", "is_read", nullable=True, server_default=None)
    op.drop_column("notifications", "type")
