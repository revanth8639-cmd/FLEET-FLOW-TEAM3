from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.core.deps import get_current_driver, get_current_user, require_roles
from app.schemas.driver import (
    DriverCreate,
    DriverUpdate,
    DriverOut,
)
from app.crud.driver import (
    create_driver,
    get_drivers,
    get_driver,
    update_driver,
    delete_driver,
    ensure_driver_profiles,
)
from app.models.vehicle import Vehicle
from app.models.driver import Driver
from app.models.user import RoleEnum, User
from app.crud.notification import add_notifications

router = APIRouter(
    prefix="/drivers",
    tags=["Drivers"]
)


def _notify_assignment(db: Session, driver_id, vehicle_id, action: str):
    driver = db.query(Driver).filter(Driver.driver_id == driver_id).first()
    users = db.query(User).filter(User.role.in_([RoleEnum.Admin, RoleEnum.FleetManager])).all()
    user_ids = [user.user_id for user in users]
    if driver and driver.user_id:
        user_ids.append(driver.user_id)
    add_notifications(db, user_ids, "Driver assignment updated", f"Driver {driver.name if driver else driver_id} was {action} vehicle {vehicle_id or 'assignment'}.", "assignment")
    db.commit()


@router.post("/", response_model=DriverOut)
def create_new_driver(
    driver: DriverCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("Admin", "FleetManager")),
):
    if driver.vehicle_id:
        vehicle = db.query(Vehicle).filter(Vehicle.vehicle_id == driver.vehicle_id).first()
        if not vehicle:
            raise HTTPException(status_code=404, detail="Assigned vehicle not found")
        if vehicle.assigned_driver_id:
            raise HTTPException(status_code=409, detail="This vehicle is already assigned to another driver")
    created = create_driver(db, driver)
    if created.vehicle_id:
        vehicle = db.query(Vehicle).filter(Vehicle.vehicle_id == created.vehicle_id).first()
        if vehicle:
            vehicle.assigned_driver_id = created.driver_id
            db.commit()
            db.refresh(created)
        _notify_assignment(db, created.driver_id, created.vehicle_id, "assigned to")
    return created


@router.get("/", response_model=list[DriverOut])
def read_drivers(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    ensure_driver_profiles(db)
    if current_user.role.value == "Driver":
        return [get_current_driver(current_user, db)]
    return get_drivers(db)


@router.get("/{driver_id}", response_model=DriverOut)
def read_driver(
    driver_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    driver = get_driver(db, driver_id)

    if not driver:
        raise HTTPException(
            status_code=404,
            detail="Driver not found"
        )

    if current_user.role.value == "Driver" and driver.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="You can view only your own driver profile")
    return driver


@router.put("/{driver_id}", response_model=DriverOut)
def update_existing_driver(
    driver_id: UUID,
    driver: DriverUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("Admin", "FleetManager")),
):
    existing = get_driver(db, driver_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Driver not found")
    previous_vehicle_id = existing.vehicle_id
    updated = update_driver(
        db,
        driver_id,
        driver,
    )

    if previous_vehicle_id != updated.vehicle_id:
        if previous_vehicle_id:
            old_vehicle = db.query(Vehicle).filter(Vehicle.vehicle_id == previous_vehicle_id, Vehicle.assigned_driver_id == updated.driver_id).first()
            if old_vehicle:
                old_vehicle.assigned_driver_id = None
        if updated.vehicle_id:
            new_vehicle = db.query(Vehicle).filter(Vehicle.vehicle_id == updated.vehicle_id).first()
            if not new_vehicle:
                updated.vehicle_id = previous_vehicle_id
                db.commit()
                raise HTTPException(status_code=404, detail="Assigned vehicle not found")
            if new_vehicle.assigned_driver_id and new_vehicle.assigned_driver_id != updated.driver_id:
                updated.vehicle_id = previous_vehicle_id
                db.commit()
                raise HTTPException(status_code=409, detail="This vehicle is already assigned to another driver")
            new_vehicle.assigned_driver_id = updated.driver_id
        db.commit()
        db.refresh(updated)
        _notify_assignment(db, updated.driver_id, updated.vehicle_id, "assigned to" if updated.vehicle_id else "unassigned from")

    return updated


@router.delete("/{driver_id}")
def delete_existing_driver(
    driver_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("Admin", "FleetManager")),
):
    try:
        deleted = delete_driver(db, driver_id)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="This driver has trip or shipment history and cannot be deleted") from error

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Driver not found"
        )

    return {
        "message": "Driver deleted successfully"
    }
