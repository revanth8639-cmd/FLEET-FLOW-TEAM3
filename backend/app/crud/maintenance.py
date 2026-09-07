from sqlalchemy.orm import Session

from app.models.maintenance import VehicleMaintenance
from app.schemas.maintenance import (
    MaintenanceCreate,
    MaintenanceUpdate,
)


def create_maintenance(db: Session, maintenance: MaintenanceCreate):
    db_maintenance = VehicleMaintenance(
        **maintenance.model_dump()
    )
    db.add(db_maintenance)
    db.commit()
    db.refresh(db_maintenance)
    return db_maintenance


def get_maintenances(db: Session):
    return db.query(VehicleMaintenance).order_by(
        VehicleMaintenance.service_date.asc(),
        VehicleMaintenance.maintenance_id.asc(),
    ).all()


def get_maintenance(db: Session, maintenance_id):
    return db.query(VehicleMaintenance).filter(
        VehicleMaintenance.maintenance_id == maintenance_id
    ).first()


def update_maintenance(db: Session, maintenance_id, maintenance: MaintenanceUpdate):
    db_maintenance = get_maintenance(db, maintenance_id)

    if not db_maintenance:
        return None

    for key, value in maintenance.model_dump(exclude_unset=True).items():
        setattr(db_maintenance, key, value)

    db.commit()
    db.refresh(db_maintenance)

    return db_maintenance


def delete_maintenance(db: Session, maintenance_id):
    db_maintenance = get_maintenance(db, maintenance_id)

    if not db_maintenance:
        return None

    db.delete(db_maintenance)
    db.commit()

    return db_maintenance
