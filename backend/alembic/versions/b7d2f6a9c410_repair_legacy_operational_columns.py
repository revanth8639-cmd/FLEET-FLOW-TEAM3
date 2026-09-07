"""Repair optional operational columns in legacy FleetFlow databases.

Revision ID: b7d2f6a9c410
Revises: f4a9c1e7d205
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "b7d2f6a9c410"
down_revision = "f4a9c1e7d205"
branch_labels = None
depends_on = None


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    existing_columns = {
        item["name"] for item in sa.inspect(op.get_bind()).get_columns(table_name)
    }
    if column.name not in existing_columns:
        op.add_column(table_name, column)


def upgrade() -> None:
    # Older databases contain the operational tables but can be missing these
    # later optional fields. Add only what is absent to preserve all records.
    _add_column_if_missing("vehicles", sa.Column("brand", sa.String(), nullable=True))
    _add_column_if_missing("vehicles", sa.Column("model", sa.String(), nullable=True))
    _add_column_if_missing("vehicles", sa.Column("manufacture_year", sa.Integer(), nullable=True))
    _add_column_if_missing(
        "vehicles", sa.Column("assigned_driver_id", postgresql.UUID(as_uuid=True), nullable=True)
    )

    _add_column_if_missing("shipments", sa.Column("customer_name", sa.String(), nullable=True))
    _add_column_if_missing("shipments", sa.Column("shipment_weight", sa.Float(), nullable=True))
    _add_column_if_missing("shipments", sa.Column("expected_delivery_at", sa.DateTime(), nullable=True))

    _add_column_if_missing("trips", sa.Column("distance_km", sa.Float(), nullable=True))
    _add_column_if_missing("trips", sa.Column("actual_distance_km", sa.Float(), nullable=True))
    _add_column_if_missing("trips", sa.Column("duration_minutes", sa.Integer(), nullable=True))
    _add_column_if_missing("trips", sa.Column("route_type", sa.String(), nullable=True))
    _add_column_if_missing("trips", sa.Column("eta", sa.DateTime(), nullable=True))
    _add_column_if_missing("trips", sa.Column("remaining_distance_km", sa.Float(), nullable=True))

    _add_column_if_missing("fuel_records", sa.Column("mileage", sa.Float(), nullable=True))
    _add_column_if_missing("fuel_records", sa.Column("refill_date", sa.DateTime(), nullable=True))


def downgrade() -> None:
    # This repair migration intentionally preserves legacy data on downgrade.
    pass
