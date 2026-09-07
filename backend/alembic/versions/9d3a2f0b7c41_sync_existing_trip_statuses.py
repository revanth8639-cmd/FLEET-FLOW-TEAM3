"""Synchronize existing trip statuses with their linked shipments.

Revision ID: 9d3a2f0b7c41
Revises: c1d4e8f2a901
Create Date: 2026-08-21
"""

from alembic import op


revision = "9d3a2f0b7c41"
down_revision = "c1d4e8f2a901"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Shipment status is the operational source of truth for a linked trip.
    op.execute(
        """
        UPDATE trips AS trip
        SET status = CASE shipment.status
            WHEN 'Created' THEN 'Scheduled'
            WHEN 'Assigned' THEN 'Scheduled'
            WHEN 'In Transit' THEN 'In Progress'
            WHEN 'Delayed' THEN 'Delayed'
            WHEN 'Delivered' THEN 'Completed'
            WHEN 'Cancelled' THEN 'Cancelled'
            ELSE trip.status
        END
        FROM shipments AS shipment
        WHERE trip.shipment_id = shipment.shipment_id
          AND shipment.status IN (
            'Created', 'Assigned', 'In Transit', 'Delayed', 'Delivered', 'Cancelled'
          )
        """
    )


def downgrade() -> None:
    # This data correction has no reliable previous value to restore.
    pass
