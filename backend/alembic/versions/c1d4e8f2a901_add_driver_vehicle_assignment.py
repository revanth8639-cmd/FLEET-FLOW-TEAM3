"""add persistent driver vehicle assignment

Revision ID: c1d4e8f2a901
Revises: a2c7e1c4d9f0
Create Date: 2026-08-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c1d4e8f2a901"
down_revision = "a2c7e1c4d9f0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("drivers", sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_drivers_vehicle_id", "drivers", "vehicles", ["vehicle_id"], ["vehicle_id"])
    op.create_unique_constraint("uq_drivers_vehicle_id", "drivers", ["vehicle_id"])


def downgrade():
    op.drop_constraint("uq_drivers_vehicle_id", "drivers", type_="unique")
    op.drop_constraint("fk_drivers_vehicle_id", "drivers", type_="foreignkey")
    op.drop_column("drivers", "vehicle_id")
