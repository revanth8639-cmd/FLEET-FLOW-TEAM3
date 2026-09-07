from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_driver, get_current_user, require_roles
from app.database import get_db
from app.models.shipment import Shipment
from app.models.trip import Trip
from app.models.vehicle import Vehicle
from app.schemas.fuel_record import FuelRecordCreate, FuelRecordUpdate, FuelRecordOut
from app.crud.fuel_record import create_fuel_record, get_fuel_records, get_fuel_record, update_fuel_record, delete_fuel_record

router = APIRouter(prefix="/fuel", tags=["Fuel Records"])


def _driver_assigned_vehicle_ids(current_user, db):
    driver = get_current_driver(current_user, db)
    vehicle_ids = set()
    if driver.vehicle_id:
        vehicle_ids.add(driver.vehicle_id)
    vehicle_ids.update(
        vehicle_id for (vehicle_id,) in db.query(Vehicle.vehicle_id)
        .filter(Vehicle.assigned_driver_id == driver.driver_id)
        .all()
    )
    # A shipment can be in any lifecycle state while its associated fuel
    # record is being entered.  Scope by driver assignment, not by a status
    # string, so the vehicle offered in the driver's shipment list is always
    # accepted by the fuel endpoint.
    vehicle_ids.update(vehicle_id for (vehicle_id,) in db.query(Shipment.vehicle_id).filter(Shipment.driver_id == driver.driver_id, Shipment.vehicle_id.isnot(None)).all())
    vehicle_ids.update(vehicle_id for (vehicle_id,) in db.query(Trip.vehicle_id).filter(Trip.driver_id == driver.driver_id).all())
    return vehicle_ids


def _can_access(fuel, current_user, db):
    if current_user.role.value != "Driver":
        return True
    return fuel.vehicle_id in _driver_assigned_vehicle_ids(current_user, db)


@router.post("/", response_model=FuelRecordOut)
def create_new_fuel_record(fuel: FuelRecordCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    if current_user.role.value in {"Admin", "FleetManager"}:
        return create_fuel_record(db, fuel)
    if current_user.role.value == "Driver":
        driver = get_current_driver(current_user, db)
        if fuel.vehicle_id not in _driver_assigned_vehicle_ids(current_user, db):
            raise HTTPException(status_code=403, detail="You can log fuel only for your assigned vehicle")
        return create_fuel_record(db, fuel.model_copy(update={"filled_by": driver.name}))
    raise HTTPException(status_code=403, detail="You can log fuel only for your assigned vehicle")


@router.get("/", response_model=list[FuelRecordOut])
def read_fuel_records(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    if current_user.role.value in {"Admin", "FleetManager", "Dispatcher"}:
        return get_fuel_records(db)
    if current_user.role.value == "Driver":
        vehicle_ids = _driver_assigned_vehicle_ids(current_user, db)
        return [record for record in get_fuel_records(db) if record.vehicle_id in vehicle_ids]
    raise HTTPException(status_code=403, detail="You do not have access to fuel records")


@router.get("/{fuel_id}", response_model=FuelRecordOut)
def read_fuel_record(fuel_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    fuel = get_fuel_record(db, fuel_id)
    if not fuel:
        raise HTTPException(status_code=404, detail="Fuel record not found")
    if not _can_access(fuel, current_user, db):
        raise HTTPException(status_code=403, detail="You do not have access to this fuel record")
    return fuel


@router.put("/{fuel_id}", response_model=FuelRecordOut)
def update_existing_fuel_record(fuel_id: UUID, fuel: FuelRecordUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    existing = get_fuel_record(db, fuel_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Fuel record not found")
    if current_user.role.value == "Dispatcher" or not _can_access(existing, current_user, db):
        raise HTTPException(status_code=403, detail="You can edit only fuel records for your assigned vehicle")
    if current_user.role.value == "Driver":
        driver = get_current_driver(current_user, db)
        fuel = FuelRecordUpdate(**{**fuel.model_dump(exclude_unset=True), "filled_by": driver.name})
    updated = update_fuel_record(db, fuel_id, fuel)
    return updated


@router.delete("/{fuel_id}")
def delete_existing_fuel_record(fuel_id: UUID, db: Session = Depends(get_db), current_user=Depends(require_roles("Admin"))):
    deleted = delete_fuel_record(db, fuel_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Fuel record not found")
    return {"message": "Fuel record deleted successfully"}
