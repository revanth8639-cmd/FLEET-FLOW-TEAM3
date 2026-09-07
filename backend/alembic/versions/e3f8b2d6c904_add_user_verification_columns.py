"""Add user email-verification fields required by the auth model.

Revision ID: e3f8b2d6c904
Revises: d2e7a9c4f511
"""
from alembic import op
import sqlalchemy as sa


revision = "e3f8b2d6c904"
down_revision = "d2e7a9c4f511"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("verification_code", sa.String(length=6), nullable=True))
    op.add_column("users", sa.Column("verification_code_expires_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "verification_code_expires_at")
    op.drop_column("users", "verification_code")
    op.drop_column("users", "email_verified")
