from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.deps import can_access_trip, get_current_driver, get_current_user, require_roles
from app.database import get_db
from app.schemas.trip import TripCreate, TripUpdate, TripOut
from app.crud.trip import create_trip, get_trips, get_trip, update_trip, delete_trip
from app.utils.routing import build_route
from app.models.driver import Driver
from app.models.shipment import Shipment
from app.models.trip import Trip
from app.models.vehicle import Vehicle
from app.models.user import RoleEnum, User
from app.crud.notification import add_notifications
from app.crud.activity import record_activity

router = APIRouter(prefix="/trips", tags=["Trips"])
ACTIVE_TRIP_STATUSES = {"Scheduled", "In Progress"}


def _trip_or_forbidden(trip_id: UUID, current_user, db: Session):
    trip = get_trip(db, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if not can_access_trip(trip, current_user, db):
        raise HTTPException(status_code=403, detail="You do not have access to this trip")
    return trip


@router.post("/", response_model=TripOut)
def create_new_trip(
    trip: TripCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("Admin", "FleetManager", "Dispatcher")),
):
    if current_user.role.value == "Dispatcher" and trip.status != "Scheduled":
        raise HTTPException(status_code=403, detail="Dispatchers can create scheduled trips only")
    shipment = db.query(Shipment).filter(Shipment.shipment_id == trip.shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Selected shipment was not found")
    # Shipment source/destination are the canonical route for a trip.
    trip.start_location = shipment.source
    trip.end_location = shipment.destination
    trip.__pydantic_fields_set__.update({"start_location", "end_location"})
    _ensure_resources_available(trip, db)
    created = create_trip(db, trip)
    _set_assignment_status(created, "Assigned", db)
    record_activity(db, current_user.user_id, "trip.created", "trip", created.trip_id)
    db.commit()
    return created


def _ensure_resources_available(trip: TripCreate | TripUpdate, db: Session, exclude_trip_id=None):
    """Prevent a driver or vehicle from being scheduled for concurrent work."""
    vehicle_id = trip.vehicle_id
    driver_id = trip.driver_id
    if vehicle_id is None or driver_id is None:
        raise HTTPException(status_code=422, detail="A trip must include a vehicle and driver")

    active = db.query(Trip).filter(Trip.status.in_(ACTIVE_TRIP_STATUSES))
    if exclude_trip_id:
        active = active.filter(Trip.trip_id != exclude_trip_id)
    if active.filter(Trip.vehicle_id == vehicle_id).first():
        raise HTTPException(status_code=409, detail="This vehicle is already assigned to an active trip")
    if active.filter(Trip.driver_id == driver_id).first():
        raise HTTPException(status_code=409, detail="This driver is already assigned to an active trip")

    vehicle = db.query(Vehicle).filter(Vehicle.vehicle_id == vehicle_id).first()
    driver = db.query(Driver).filter(Driver.driver_id == driver_id).first()
    if not vehicle or not driver:
        raise HTTPException(status_code=404, detail="Selected vehicle or driver was not found")
    if vehicle.status in {"Maintenance", "Unavailable"}:
        raise HTTPException(status_code=409, detail="This vehicle is not available for a trip")


def _set_assignment_status(trip, status: str, db: Session):
    vehicle = db.query(Vehicle).filter(Vehicle.vehicle_id == trip.vehicle_id).first()
    driver = db.query(Driver).filter(Driver.driver_id == trip.driver_id).first()
    if vehicle:
        vehicle.status = status
    if driver:
        driver.status = status
    db.commit()


@router.get("/", response_model=list[TripOut])
def read_trips(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    trips = get_trips(db)
    return [trip for trip in trips if can_access_trip(trip, current_user, db)]


def _calculate_route(trip_id: UUID, route_type: str, db: Session, current_user):
    trip = _trip_or_forbidden(trip_id, current_user, db)
    # _trip_or_forbidden already limits Driver accounts to their own trips.
    # Route calculation is read-only, so drivers may optimize their assigned
    # route without gaining access to fleet-management actions.
    try:
        route = build_route(trip.start_location, trip.end_location, route_type)
        trip.route_type = route_type
        trip.distance_km = route["distance_km"]
        trip.duration_minutes = route["duration_minutes"]
        trip.eta = datetime.fromisoformat(route["eta"])
        db.commit(); db.refresh(trip)
        users = db.query(User).filter(User.role.in_([RoleEnum.Admin, RoleEnum.FleetManager, RoleEnum.Dispatcher])).all()
        add_notifications(db, [user.user_id for user in users], "Route recalculated", f"Route for trip {trip.trip_id} was recalculated using {route_type}.", "route")
        record_activity(db, current_user.user_id, "trip.route_recalculated", "trip", trip.trip_id)
        db.commit()
        return {**route, "trip_id": str(trip.trip_id)}
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/{trip_id}/route")
def read_trip_route(trip_id: UUID, route_type: str = "Fastest Route", db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return _calculate_route(trip_id, route_type, db, current_user)


@router.post("/{trip_id}/recalculate")
def recalculate_trip_route(trip_id: UUID, route_type: str = "Fastest Route", db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return _calculate_route(trip_id, route_type, db, current_user)


@router.get("/{trip_id}", response_model=TripOut)
def read_trip(trip_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return _trip_or_forbidden(trip_id, current_user, db)


def _sync_lifecycle(trip, started: bool, db: Session):
    shipment = db.query(Shipment).filter(Shipment.shipment_id == trip.shipment_id).first()
    vehicle = db.query(Vehicle).filter(Vehicle.vehicle_id == trip.vehicle_id).first()
    driver = db.query(Driver).filter(Driver.driver_id == trip.driver_id).first()
    if started:
        trip.status, trip.start_time = "In Progress", datetime.utcnow()
        if shipment: shipment.status = "In Transit"
        if vehicle: vehicle.status = "In Transit"
        if driver: driver.status = "On Trip"
    else:
        trip.status, trip.end_time = "Completed", datetime.utcnow()
        if shipment: shipment.status = "Delivered"
        if vehicle: vehicle.status = "Available"
        if driver: driver.status = "Available"
    users = db.query(User).filter(User.role.in_([RoleEnum.Admin, RoleEnum.FleetManager, RoleEnum.Dispatcher])).all()
    user_ids = [user.user_id for user in users]
    if driver and driver.user_id:
        user_ids.append(driver.user_id)
    event = "started" if started else "delivered"
    add_notifications(db, user_ids, f"Trip {event}", f"Trip {trip.trip_id} has {event}.", "shipment")
    db.commit(); db.refresh(trip)
    return trip


@router.post("/{trip_id}/start", response_model=TripOut)
def start_trip(trip_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    trip = _trip_or_forbidden(trip_id, current_user, db)
    if current_user.role.value not in {"Admin", "FleetManager", "Driver"}:
        raise HTTPException(status_code=403, detail="You do not have permission to start trips")
    if trip.status != "Scheduled":
        raise HTTPException(status_code=400, detail="Only a scheduled trip can be started")
    return _sync_lifecycle(trip, started=True, db=db)


@router.post("/{trip_id}/end", response_model=TripOut)
def end_trip(trip_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    trip = _trip_or_forbidden(trip_id, current_user, db)
    if current_user.role.value not in {"Admin", "FleetManager", "Driver"}:
        raise HTTPException(status_code=403, detail="You do not have permission to end trips")
    if trip.status != "In Progress":
        raise HTTPException(status_code=400, detail="Only an in-progress trip can be ended")
    return _sync_lifecycle(trip, started=False, db=db)


@router.put("/{trip_id}", response_model=TripOut)
def update_existing_trip(trip_id: UUID, trip: TripUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    existing = _trip_or_forbidden(trip_id, current_user, db)
    linked_shipment = db.query(Shipment).filter(Shipment.shipment_id == (trip.shipment_id or existing.shipment_id)).first()
    if not linked_shipment:
        raise HTTPException(status_code=404, detail="Selected shipment was not found")
    trip.start_location = linked_shipment.source
    trip.end_location = linked_shipment.destination
    trip.__pydantic_fields_set__.update({"start_location", "end_location"})
    previous_vehicle_id, previous_driver_id, previous_status = existing.vehicle_id, existing.driver_id, existing.status
    if current_user.role.value == "Driver":
        # Drivers may only update the lifecycle of their own trip.
        changes = trip.model_dump(exclude_unset=True)
        if set(changes) - {"status", "start_time", "end_time"}:
            raise HTTPException(status_code=403, detail="Drivers may only start or end their own trip")
        if changes.get("status") not in {None, "In Progress", "Completed"}:
            raise HTTPException(status_code=400, detail="Invalid driver trip status")
    elif current_user.role.value == "Dispatcher":
        changes = trip.model_dump(exclude_unset=True)
        dispatch_fields = {"vehicle_id", "driver_id", "shipment_id", "start_location", "end_location", "route_type", "status"}
        if set(changes) - dispatch_fields or changes.get("status") not in {None, "Scheduled"}:
            raise HTTPException(
                status_code=403,
                detail="Dispatchers may coordinate scheduled trips but cannot change trip lifecycle data",
            )
    elif current_user.role.value not in {"Admin", "FleetManager", "Dispatcher"}:
        raise HTTPException(status_code=403, detail="You do not have permission to update trips")
    if current_user.role.value in {"Admin", "FleetManager", "Dispatcher"}:
        merged = TripUpdate(
            **{
                "vehicle_id": trip.vehicle_id or existing.vehicle_id,
                "driver_id": trip.driver_id or existing.driver_id,
            }
        )
        _ensure_resources_available(merged, db, exclude_trip_id=existing.trip_id)
    updated = update_trip(db, existing.trip_id, trip)
    record_activity(db, current_user.user_id, "trip.updated", "trip", updated.trip_id)
    if updated.status in ACTIVE_TRIP_STATUSES:
        _set_assignment_status(updated, "Assigned" if updated.status == "Scheduled" else "In Transit", db)
    if previous_status in ACTIVE_TRIP_STATUSES:
        remaining = db.query(Trip).filter(Trip.status.in_(ACTIVE_TRIP_STATUSES), Trip.trip_id != updated.trip_id)
        if previous_vehicle_id != updated.vehicle_id and not remaining.filter(Trip.vehicle_id == previous_vehicle_id).first():
            old_vehicle = db.query(Vehicle).filter(Vehicle.vehicle_id == previous_vehicle_id).first()
            if old_vehicle:
                old_vehicle.status = "Available"
        if previous_driver_id != updated.driver_id and not remaining.filter(Trip.driver_id == previous_driver_id).first():
            old_driver = db.query(Driver).filter(Driver.driver_id == previous_driver_id).first()
            if old_driver:
                old_driver.status = "Available"
        db.commit()
    else:
        db.commit()
    return updated


@router.delete("/{trip_id}")
def delete_existing_trip(trip_id: UUID, db: Session = Depends(get_db), current_user=Depends(require_roles("Admin"))):
    existing = get_trip(db, trip_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Trip not found")
    vehicle_id, driver_id = existing.vehicle_id, existing.driver_id
    try:
        deleted = delete_trip(db, trip_id)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="This trip has tracking or shipment history and cannot be deleted") from error
    remaining = db.query(Trip).filter(Trip.status.in_(ACTIVE_TRIP_STATUSES))
    if not remaining.filter(Trip.vehicle_id == vehicle_id).first():
        vehicle = db.query(Vehicle).filter(Vehicle.vehicle_id == vehicle_id).first()
        if vehicle:
            vehicle.status = "Available"
    if not remaining.filter(Trip.driver_id == driver_id).first():
        driver = db.query(Driver).filter(Driver.driver_id == driver_id).first()
        if driver:
            driver.status = "Available"
    db.commit()
    record_activity(db, current_user.user_id, "trip.deleted", "trip", trip_id)
    db.commit()
    return {"message": "Trip deleted successfully"}
