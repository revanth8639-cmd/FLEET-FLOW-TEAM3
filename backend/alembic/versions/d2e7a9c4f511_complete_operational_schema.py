"""Complete FleetFlow operational fields and shipment status history.

Revision ID: d2e7a9c4f511
Revises: 9d3a2f0b7c41
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "d2e7a9c4f511"
down_revision = "9d3a2f0b7c41"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vehicles", sa.Column("brand", sa.String(), nullable=True))
    op.add_column("vehicles", sa.Column("model", sa.String(), nullable=True))
    op.add_column("vehicles", sa.Column("manufacture_year", sa.Integer(), nullable=True))
    op.add_column("vehicles", sa.Column("assigned_driver_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_vehicles_assigned_driver", "vehicles", "drivers", ["assigned_driver_id"], ["driver_id"])
    op.create_unique_constraint("uq_vehicles_assigned_driver", "vehicles", ["assigned_driver_id"])

    op.add_column("shipments", sa.Column("customer_name", sa.String(), nullable=True))
    op.add_column("shipments", sa.Column("shipment_weight", sa.Float(), nullable=True))
    op.add_column("shipments", sa.Column("expected_delivery_at", sa.DateTime(), nullable=True))
    op.create_index("ix_shipments_customer_name", "shipments", ["customer_name"])

    op.add_column("trips", sa.Column("distance_km", sa.Float(), nullable=True))
    op.add_column("trips", sa.Column("actual_distance_km", sa.Float(), nullable=True))
    op.add_column("trips", sa.Column("duration_minutes", sa.Integer(), nullable=True))
    op.add_column("trips", sa.Column("route_type", sa.String(), nullable=True))
    op.add_column("trips", sa.Column("eta", sa.DateTime(), nullable=True))
    op.add_column("trips", sa.Column("remaining_distance_km", sa.Float(), nullable=True))

    op.add_column("fuel_records", sa.Column("mileage", sa.Float(), nullable=True))
    op.add_column("fuel_records", sa.Column("refill_date", sa.DateTime(), nullable=True))

    op.create_table(
        "shipment_status_history",
        sa.Column("history_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("shipment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("shipments.shipment_id"), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("changed_at", sa.DateTime(), nullable=False),
        sa.Column("changed_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=True),
    )
    op.create_index("ix_shipment_status_history_shipment_id", "shipment_status_history", ["shipment_id"])


def downgrade() -> None:
    op.drop_index("ix_shipment_status_history_shipment_id", table_name="shipment_status_history")
    op.drop_table("shipment_status_history")
    op.drop_column("fuel_records", "refill_date")
    op.drop_column("fuel_records", "mileage")
    for column in ("remaining_distance_km", "eta", "route_type", "duration_minutes", "actual_distance_km", "distance_km"):
        op.drop_column("trips", column)
    op.drop_index("ix_shipments_customer_name", table_name="shipments")
    for column in ("expected_delivery_at", "shipment_weight", "customer_name"):
        op.drop_column("shipments", column)
    op.drop_constraint("uq_vehicles_assigned_driver", "vehicles", type_="unique")
    op.drop_constraint("fk_vehicles_assigned_driver", "vehicles", type_="foreignkey")
    for column in ("assigned_driver_id", "manufacture_year", "model", "brand"):
        op.drop_column("vehicles", column)
