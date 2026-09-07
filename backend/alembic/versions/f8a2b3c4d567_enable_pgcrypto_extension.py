"""Enable PostgreSQL crypto/UUID extension required by the milestone schema."""

from alembic import op


revision = "f8a2b3c4d567"
down_revision = "e7f1a9c3d205"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')


def downgrade() -> None:
    op.execute('DROP EXTENSION IF EXISTS "pgcrypto"')
