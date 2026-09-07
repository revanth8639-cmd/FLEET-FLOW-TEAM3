from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_current_driver, get_current_user, require_roles

from app.schemas.vehicle import (
    VehicleCreate,
    VehicleUpdate,
    VehicleOut,
)

from app.crud.vehicle import (
    create_vehicle,
    get_vehicles,
    get_vehicle,
    update_vehicle,
    delete_vehicle,
)
from app.models.trip import Trip
from app.models.driver import Driver
from app.models.vehicle import Vehicle
from app.models.user import RoleEnum, User
from app.crud.notification import add_notifications
from app.crud.activity import record_activity


router = APIRouter(
    prefix="/vehicles",
    tags=["Vehicles"]
)


def _driver_vehicle_ids(driver, db: Session):
    vehicle_ids = {driver.vehicle_id} if driver.vehicle_id else set()
    vehicle_ids.update(
        vehicle_id for (vehicle_id,) in db.query(Vehicle.vehicle_id)
        .filter(Vehicle.assigned_driver_id == driver.driver_id)
        .all()
    )
    vehicle_ids.update(
        vehicle_id for (vehicle_id,) in db.query(Trip.vehicle_id)
        .filter(Trip.driver_id == driver.driver_id, Trip.vehicle_id.isnot(None))
        .all()
    )
    return vehicle_ids


# CREATE VEHICLE
# Admin + Fleet Manager only
@router.post("/", response_model=VehicleOut)
def create_new_vehicle(
    vehicle: VehicleCreate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles("Admin", "FleetManager")
    ),
):
    if vehicle.assigned_driver_id:
        driver = db.query(Driver).filter(Driver.driver_id == vehicle.assigned_driver_id).first()
        if not driver:
            raise HTTPException(status_code=404, detail="Assigned driver not found")
        if driver.vehicle_id:
            raise HTTPException(status_code=409, detail="This driver is already assigned to another vehicle")
    created = create_vehicle(db, vehicle)
    record_activity(db, current_user.user_id, "vehicle.created", "vehicle", created.vehicle_id)
    if created.assigned_driver_id:
        driver = db.query(Driver).filter(Driver.driver_id == created.assigned_driver_id).first()
        if driver:
            driver.vehicle_id = created.vehicle_id
            db.commit()
            db.refresh(created)
    db.commit()
    return created


# READ ALL VEHICLES
# All authenticated users
@router.get("/", response_model=list[VehicleOut])
def read_vehicles(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role.value != "Driver":
        return get_vehicles(db)
    driver = get_current_driver(current_user, db)
    # A driver's persistent vehicle assignment may differ from a vehicle on
    # one of their completed or active trips.  Expose only those vehicles so
    # the driver can identify every trip shown in their own history.
    vehicle_ids = _driver_vehicle_ids(driver, db)
    if not vehicle_ids:
        return []
    return db.query(Vehicle).filter(Vehicle.vehicle_id.in_(vehicle_ids)).all()


# READ ONE VEHICLE
# All authenticated users
@router.get("/{vehicle_id}", response_model=VehicleOut)
def read_vehicle(
    vehicle_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role.value == "Driver":
        driver = get_current_driver(current_user, db)
        if vehicle_id not in _driver_vehicle_ids(driver, db):
            raise HTTPException(status_code=403, detail="You can view only your assigned vehicle")

    vehicle = get_vehicle(db, vehicle_id)

    if not vehicle:
        raise HTTPException(
            status_code=404,
            detail="Vehicle not found"
        )

    return vehicle


# UPDATE VEHICLE
# Admin + Fleet Manager only
@router.put("/{vehicle_id}", response_model=VehicleOut)
def update_existing_vehicle(
    vehicle_id: UUID,
    vehicle: VehicleUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles("Admin", "FleetManager")
    ),
):
    existing = get_vehicle(db, vehicle_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    previous_driver_id = existing.assigned_driver_id
    changes = vehicle.model_dump(exclude_unset=True)
    updated = update_vehicle(
        db,
        vehicle_id,
        vehicle
    )

    if "assigned_driver_id" in changes and previous_driver_id != updated.assigned_driver_id:
        if previous_driver_id:
            old_driver = db.query(Driver).filter(Driver.driver_id == previous_driver_id, Driver.vehicle_id == updated.vehicle_id).first()
            if old_driver:
                old_driver.vehicle_id = None
        if updated.assigned_driver_id:
            new_driver = db.query(Driver).filter(Driver.driver_id == updated.assigned_driver_id).first()
            if not new_driver:
                updated.assigned_driver_id = previous_driver_id
                db.commit()
                raise HTTPException(status_code=404, detail="Assigned driver not found")
            if new_driver.vehicle_id and new_driver.vehicle_id != updated.vehicle_id:
                updated.assigned_driver_id = previous_driver_id
                db.commit()
                raise HTTPException(status_code=409, detail="This driver is already assigned to another vehicle")
            new_driver.vehicle_id = updated.vehicle_id
        db.commit()
        db.refresh(updated)
        users = db.query(User).filter(User.role.in_([RoleEnum.Admin, RoleEnum.FleetManager])).all()
        user_ids = [user.user_id for user in users]
        if updated.assigned_driver_id:
            assigned_driver = db.query(Driver).filter(Driver.driver_id == updated.assigned_driver_id).first()
            if assigned_driver and assigned_driver.user_id:
                user_ids.append(assigned_driver.user_id)
        add_notifications(db, user_ids, "Vehicle assignment updated", f"Vehicle {updated.registration_number} driver assignment was updated.", "assignment")
        db.commit()

    record_activity(db, current_user.user_id, "vehicle.updated", "vehicle", updated.vehicle_id)
    db.commit()
    return updated


# DELETE VEHICLE
# Fleet Managers manage fleet records, including deleting unused vehicles.
@router.delete("/{vehicle_id}")
def delete_existing_vehicle(
    vehicle_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles("Admin", "FleetManager")
    ),
):
    try:
        deleted = delete_vehicle(db, vehicle_id)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="This vehicle has trip or tracking history and cannot be deleted") from error

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Vehicle not found"
        )

    record_activity(db, current_user.user_id, "vehicle.deleted", "vehicle", vehicle_id)
    db.commit()
    return {
        "message": "Vehicle deleted successfully"
    }
