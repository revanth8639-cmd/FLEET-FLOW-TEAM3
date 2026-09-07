"""Add the email OTP table used by signup.

Revision ID: f4a9c1e7d205
Revises: e3f8b2d6c904
"""
from alembic import op
import sqlalchemy as sa


revision = "f4a9c1e7d205"
down_revision = "e3f8b2d6c904"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "email_otps",
        sa.Column("email", sa.String(length=100), primary_key=True),
        sa.Column("otp", sa.String(length=6), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("email_otps")
