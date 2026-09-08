"""Repair indexes and constraints required by FleetFlow operational models.

Some existing databases were stamped at the current revision after an earlier
manual schema update, leaving the optional shipment index and vehicle-driver
constraints absent.  Each repair is conditional so upgrades preserve both
fresh installations and already-correct databases.
"""

from alembic import op
import sqlalchemy as sa


revision = "f9b3c4d5e678"
down_revision = "f8a2b3c4d567"
branch_labels = None
depends_on = None


def _index_exists(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def _constraint_exists(constraints: list[dict], name: str) -> bool:
    return any(constraint.get("name") == name for constraint in constraints)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _index_exists(inspector, "shipments", "ix_shipments_customer_name"):
        op.create_index("ix_shipments_customer_name", "shipments", ["customer_name"])

    vehicle_foreign_keys = inspector.get_foreign_keys("vehicles")
    if not _constraint_exists(vehicle_foreign_keys, "fk_vehicles_assigned_driver"):
        op.create_foreign_key(
            "fk_vehicles_assigned_driver",
            "vehicles",
            "drivers",
            ["assigned_driver_id"],
            ["driver_id"],
        )

    vehicle_unique_constraints = inspector.get_unique_constraints("vehicles")
    if not _constraint_exists(vehicle_unique_constraints, "uq_vehicles_assigned_driver"):
        op.create_unique_constraint("uq_vehicles_assigned_driver", "vehicles", ["assigned_driver_id"])

    user_checks = inspector.get_check_constraints("users")
    if not _constraint_exists(user_checks, "users_role_check"):
        op.create_check_constraint(
            "users_role_check",
            "users",
            "role IN ('Admin', 'FleetManager', 'Driver', 'Dispatcher')",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _constraint_exists(inspector.get_check_constraints("users"), "users_role_check"):
        op.drop_constraint("users_role_check", "users", type_="check")
    if _constraint_exists(inspector.get_unique_constraints("vehicles"), "uq_vehicles_assigned_driver"):
        op.drop_constraint("uq_vehicles_assigned_driver", "vehicles", type_="unique")
    if _constraint_exists(inspector.get_foreign_keys("vehicles"), "fk_vehicles_assigned_driver"):
        op.drop_constraint("fk_vehicles_assigned_driver", "vehicles", type_="foreignkey")
    if _index_exists(inspector, "shipments", "ix_shipments_customer_name"):
        op.drop_index("ix_shipments_customer_name", table_name="shipments")
