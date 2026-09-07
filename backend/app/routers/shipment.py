from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.deps import get_current_driver, get_current_user, require_roles
from app.database import get_db
from app.models.driver import Driver
from app.models.trip import Trip
from app.models.shipment_history import ShipmentStatusHistory
from app.models.user import RoleEnum, User
from app.crud.notification import add_notifications
from app.crud.activity import record_activity
from app.schemas.shipment import ShipmentCreate, ShipmentUpdate, ShipmentOut
from app.schemas.shipment_history import ShipmentHistoryOut
from app.crud.shipment import create_shipment, get_shipments, get_shipment, update_shipment, delete_shipment

router = APIRouter(prefix="/shipments", tags=["Shipments"])


class ShipmentStatusUpdate(BaseModel):
    status: str


SHIPMENT_TO_TRIP_STATUS = {
    "Created": "Scheduled",
    "Assigned": "Scheduled",
    "In Transit": "In Progress",
    "Delayed": "Delayed",
    "Delivered": "Completed",
    "Cancelled": "Cancelled",
}


def _sync_linked_trip_status(shipment_id: UUID, shipment_status: str, db: Session) -> None:
    """Keep the operational trip status aligned with its shipment."""
    trip_status = SHIPMENT_TO_TRIP_STATUS.get(shipment_status)
    if trip_status:
        db.query(Trip).filter(Trip.shipment_id == shipment_id).update(
            {"status": trip_status}, synchronize_session=False
        )


def _may_access(shipment, current_user: object, db: Session) -> bool:
    if current_user.role.value != "Driver":
        return True
    driver = db.query(Driver).filter(Driver.user_id == current_user.user_id).first()
    return bool(driver and shipment.driver_id == driver.driver_id)


def _record_status(shipment_id: UUID, status: str, user_id: UUID, db: Session) -> None:
    db.add(ShipmentStatusHistory(shipment_id=shipment_id, status=status, changed_by_user_id=user_id))


def _notify_status_change(shipment, status: str, db: Session) -> None:
    """Notify operational roles and the assigned driver about shipment events."""
    users = db.query(User).filter(User.role.in_([RoleEnum.Admin, RoleEnum.FleetManager, RoleEnum.Dispatcher])).all()
    user_ids = [user.user_id for user in users]
    if shipment.driver_id:
        driver = db.query(Driver).filter(Driver.driver_id == shipment.driver_id).first()
        if driver and driver.user_id:
            user_ids.append(driver.user_id)
    if status in {"Delivered", "Delayed", "Cancelled"}:
        add_notifications(db, user_ids, f"Shipment {status}", f"Shipment {shipment.tracking_number} is now {status.lower()}.", "shipment")


@router.post("/", response_model=ShipmentOut)
def create_new_shipment(shipment: ShipmentCreate, db: Session = Depends(get_db), current_user=Depends(require_roles("Admin", "FleetManager", "Dispatcher"))):
    if current_user.role.value == "Dispatcher" and (shipment.vehicle_id or shipment.driver_id):
        raise HTTPException(
            status_code=403,
            detail="Dispatchers can create unassigned shipments but cannot assign vehicles or drivers",
        )
    created = create_shipment(db, shipment)
    _record_status(created.shipment_id, created.status, current_user.user_id, db)
    record_activity(db, current_user.user_id, "shipment.created", "shipment", created.shipment_id)
    db.commit()
    return created


@router.get("/", response_model=list[ShipmentOut])
def read_shipments(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    shipments = get_shipments(db)
    if current_user.role.value != "Driver":
        return shipments
    driver = db.query(Driver).filter(Driver.user_id == current_user.user_id).first()
    return [] if not driver else [shipment for shipment in shipments if shipment.driver_id == driver.driver_id]


@router.get("/{shipment_id}/history", response_model=list[ShipmentHistoryOut])
def read_shipment_history(shipment_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    shipment = get_shipment(db, shipment_id)
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    if not _may_access(shipment, current_user, db):
        raise HTTPException(status_code=403, detail="You do not have access to this shipment")
    return db.query(ShipmentStatusHistory).filter(ShipmentStatusHistory.shipment_id == shipment_id).order_by(ShipmentStatusHistory.changed_at.asc()).all()


@router.get("/{shipment_id}", response_model=ShipmentOut)
def read_shipment(shipment_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    shipment = get_shipment(db, shipment_id)
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    if not _may_access(shipment, current_user, db):
        raise HTTPException(status_code=403, detail="You do not have access to this shipment")
    return shipment


@router.put("/{shipment_id}", response_model=ShipmentOut)
def update_existing_shipment(shipment_id: UUID, shipment: ShipmentUpdate, db: Session = Depends(get_db), current_user=Depends(require_roles("Admin", "FleetManager", "Dispatcher"))):
    changes = shipment.model_dump(exclude_unset=True)
    if current_user.role.value == "Dispatcher":
        if set(changes) - {"status"}:
            raise HTTPException(
                status_code=403,
                detail="Dispatchers can update shipment status only",
            )
    updated = update_shipment(db, shipment_id, shipment)
    if not updated:
        raise HTTPException(status_code=404, detail="Shipment not found")
    # A scheduled trip has not started yet, so it should use the latest
    # shipment pickup and delivery locations.  Once a trip starts, preserve
    # its recorded route as operational history.
    route_changes = {
        trip_field: changes[shipment_field]
        for shipment_field, trip_field in (("source", "start_location"), ("destination", "end_location"))
        if shipment_field in changes
    }
    if route_changes:
        db.query(Trip).filter(
            Trip.shipment_id == shipment_id,
            Trip.status == "Scheduled",
        ).update(route_changes, synchronize_session=False)
    if "status" in changes:
        _sync_linked_trip_status(shipment_id, updated.status, db)
        _record_status(shipment_id, updated.status, current_user.user_id, db)
        _notify_status_change(updated, updated.status, db)
        record_activity(db, current_user.user_id, "shipment.status_updated", "shipment", updated.shipment_id)
    elif changes:
        record_activity(db, current_user.user_id, "shipment.updated", "shipment", updated.shipment_id)
    if route_changes or "status" in changes:
        db.commit()
    return updated


@router.put("/{shipment_id}/status")
def update_shipment_status(shipment_id: UUID, data: ShipmentStatusUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    shipment = get_shipment(db, shipment_id)
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    if current_user.role.value not in {"Admin", "FleetManager", "Dispatcher", "Driver"}:
        raise HTTPException(status_code=403, detail="You do not have permission to update shipment status")
    if current_user.role.value == "Driver" and not _may_access(shipment, current_user, db):
        raise HTTPException(status_code=403, detail="You can update only your assigned shipments")
    if data.status not in {"Created", "Assigned", "In Transit", "Delayed", "Delivered", "Cancelled"}:
        raise HTTPException(status_code=400, detail="Invalid shipment status")
    shipment.status = data.status
    _sync_linked_trip_status(shipment_id, data.status, db)
    _record_status(shipment_id, data.status, current_user.user_id, db)
    _notify_status_change(shipment, data.status, db)
    record_activity(db, current_user.user_id, "shipment.status_updated", "shipment", shipment_id)
    db.commit(); db.refresh(shipment)
    return {"message": "Shipment status updated successfully", "shipment_id": str(shipment.shipment_id), "status": shipment.status}


@router.delete("/{shipment_id}")
def delete_existing_shipment(shipment_id: UUID, db: Session = Depends(get_db), current_user=Depends(require_roles("Admin"))):
    try:
        deleted = delete_shipment(db, shipment_id)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="This shipment has trip or status history and cannot be deleted") from error
    if not deleted:
        raise HTTPException(status_code=404, detail="Shipment not found")
    record_activity(db, current_user.user_id, "shipment.deleted", "shipment", shipment_id)
    db.commit()
    return {"message": "Shipment deleted successfully"}
