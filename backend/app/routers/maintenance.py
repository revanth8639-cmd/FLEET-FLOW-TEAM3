from uuid import UUID
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_driver, get_current_user, require_roles
from app.database import get_db
from app.models.vehicle import Vehicle
from app.models.driver import Driver
from app.models.user import RoleEnum, User
from app.crud.notification import add_notifications
from app.crud.activity import record_activity
from app.schemas.maintenance import MaintenanceCreate, MaintenanceUpdate, MaintenanceOut
from app.crud.maintenance import create_maintenance, get_maintenances, get_maintenance, update_maintenance, delete_maintenance

router = APIRouter(prefix="/maintenance", tags=["Maintenance"])


def _notify_maintenance(record, db: Session, message: str):
    users = db.query(User).filter(User.role.in_([RoleEnum.Admin, RoleEnum.FleetManager])).all()
    user_ids = [user.user_id for user in users]
    driver = db.query(Driver).filter(Driver.vehicle_id == record.vehicle_id).first()
    if driver and driver.user_id:
        user_ids.append(driver.user_id)
    add_notifications(db, user_ids, "Maintenance scheduled", message, "maintenance")
    db.commit()


def _visible(records, current_user, db):
    if current_user.role.value != "Driver":
        return records
    driver = get_current_driver(current_user, db)
    return [record for record in records if record.vehicle_id == driver.vehicle_id]


@router.post("/", response_model=MaintenanceOut)
def create_new_maintenance(maintenance: MaintenanceCreate, db: Session = Depends(get_db), current_user=Depends(require_roles("Admin", "FleetManager"))):
    record = create_maintenance(db, maintenance)
    record_activity(db, current_user.user_id, "maintenance.created", "maintenance", record.maintenance_id)
    if (record.status or "").lower() not in {"completed", "resolved"}:
        vehicle = db.query(Vehicle).filter(Vehicle.vehicle_id == record.vehicle_id).first()
        if vehicle:
            vehicle.status = "Maintenance"; db.commit()
        _notify_maintenance(record, db, f"{record.service_type} maintenance is scheduled for vehicle {record.vehicle_id}.")
    db.commit()
    return record


@router.get("/", response_model=list[MaintenanceOut])
def read_maintenances(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return _visible(get_maintenances(db), current_user, db)


@router.get("/vehicle/{vehicle_id}", response_model=list[MaintenanceOut])
def read_vehicle_maintenance_history(vehicle_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    records = get_maintenances(db)
    if current_user.role.value == "Driver":
        visible = _visible(records, current_user, db)
        if not any(record.vehicle_id == vehicle_id for record in visible):
            raise HTTPException(status_code=403, detail="You can view maintenance only for your assigned vehicle")
    return [record for record in records if record.vehicle_id == vehicle_id]


@router.get("/upcoming-overdue", response_model=list[MaintenanceOut])
def read_upcoming_or_overdue_maintenance(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("Admin", "FleetManager")),
):
    cutoff = datetime.utcnow() + timedelta(days=7)
    return [
        record for record in get_maintenances(db)
        if not record.is_resolved and record.alert_due_date and record.alert_due_date <= cutoff
    ]


@router.get("/{maintenance_id}", response_model=MaintenanceOut)
def read_maintenance(maintenance_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    record = get_maintenance(db, maintenance_id)
    if not record:
        raise HTTPException(status_code=404, detail="Maintenance record not found")
    if record not in _visible([record], current_user, db):
        raise HTTPException(status_code=403, detail="You do not have access to this maintenance record")
    return record


@router.put("/{maintenance_id}", response_model=MaintenanceOut)
def update_existing_maintenance(maintenance_id: UUID, maintenance: MaintenanceUpdate, db: Session = Depends(get_db), current_user=Depends(require_roles("Admin", "FleetManager"))):
    record = update_maintenance(db, maintenance_id, maintenance)
    if not record:
        raise HTTPException(status_code=404, detail="Maintenance record not found")
    vehicle = db.query(Vehicle).filter(Vehicle.vehicle_id == record.vehicle_id).first()
    if vehicle:
        vehicle.status = "Available" if (record.status or "").lower() in {"completed", "resolved"} else "Maintenance"; db.commit()
    if (maintenance.status or "").lower() in {"completed", "resolved"}:
        _notify_maintenance(record, db, f"Maintenance for vehicle {record.vehicle_id} has been resolved.")
    record_activity(db, current_user.user_id, "maintenance.updated", "maintenance", record.maintenance_id)
    db.commit()
    return record


@router.delete("/{maintenance_id}")
def delete_existing_maintenance(maintenance_id: UUID, db: Session = Depends(get_db), current_user=Depends(require_roles("Admin"))):
    deleted = delete_maintenance(db, maintenance_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Maintenance record not found")
    record_activity(db, current_user.user_id, "maintenance.deleted", "maintenance", maintenance_id)
    db.commit()
    return {"message": "Maintenance record deleted successfully"}
