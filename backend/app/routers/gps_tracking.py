from uuid import UUID
from datetime import datetime
from math import asin, cos, radians, sin, sqrt
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.deps import get_current_driver, get_current_user, require_roles
from app.core.security import ALGORITHM, SECRET_KEY
from app.database import get_db
from app.models.shipment import Shipment
from app.models.trip import Trip
from app.utils.routing import build_route
from app.schemas.gps_tracking import GPSTrackingCreate, GPSTrackingOut
from app.crud.gps_tracking import create_gps_tracking, get_latest_locations, get_latest_location, get_tracking_history
from app.crud.user import get_user_by_email
from app.database import SessionLocal
from app.utils.websocket_manager import gps_connections

router = APIRouter(prefix="/gps", tags=["GPS Tracking"])


def _driver_vehicle_ids(current_user, db: Session) -> set:
    """Return only vehicles that the authenticated driver may operate."""
    driver = get_current_driver(current_user, db)
    vehicle_ids = {driver.vehicle_id} if driver.vehicle_id else set()
    vehicle_ids.update(
        vehicle_id for (vehicle_id,) in db.query(Shipment.vehicle_id)
        .filter(Shipment.driver_id == driver.driver_id, Shipment.vehicle_id.is_not(None)).all()
    )
    vehicle_ids.update(
        vehicle_id for (vehicle_id,) in db.query(Trip.vehicle_id)
        .filter(Trip.driver_id == driver.driver_id, Trip.vehicle_id.is_not(None)).all()
    )
    return vehicle_ids


def _enforce_vehicle_scope(vehicle_id: UUID, current_user, db: Session):
    if current_user.role.value != "Driver":
        return
    if vehicle_id not in _driver_vehicle_ids(current_user, db):
        raise HTTPException(status_code=403, detail="You can access GPS only for your assigned vehicle")


def _location_event(location) -> dict:
    return {
        "type": "gps_location",
        "location": GPSTrackingOut.model_validate(location).model_dump(mode="json"),
    }


def _refresh_active_trip_eta(location, db: Session) -> None:
    """Recalculate only the active trip for the moving vehicle."""
    trip = db.query(Trip).filter(Trip.vehicle_id == location.vehicle_id, Trip.status == "In Progress").first()
    if not trip:
        return
    try:
        route = build_route(f"{location.latitude},{location.longitude}", trip.end_location, trip.route_type or "Fastest Route")
        trip.remaining_distance_km = route["distance_km"]
        trip.eta = datetime.fromisoformat(route["eta"])
        db.commit()
    except Exception:
        db.rollback()


@router.post("/", response_model=GPSTrackingOut)
async def add_gps_location(gps_data: GPSTrackingCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    _enforce_vehicle_scope(gps_data.vehicle_id, current_user, db)
    if current_user.role.value not in {"Admin", "FleetManager", "Driver"}:
        raise HTTPException(status_code=403, detail="You do not have permission to publish GPS locations")
    location = create_gps_tracking(db, gps_data)
    _refresh_active_trip_eta(location, db)
    await gps_connections.publish(_location_event(location))
    return location


@router.websocket("/ws")
async def gps_websocket(websocket: WebSocket, token: str | None = None):
    """Stream and publish GPS events using the normal JWT authorization model.

    Send ``{\"vehicle_id\": ..., \"latitude\": ..., \"longitude\": ...}``
    messages from a driver/vehicle client.  Every connected dashboard client
    receives a ``gps_location`` event after the location has been persisted.
    Clients can reconnect with the same ``?token=<JWT>`` URL at any time.
    """
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    db = SessionLocal()
    try:
        try:
            email = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]).get("sub")
        except JWTError:
            email = None
        current_user = get_user_by_email(db, email) if email else None
        if not current_user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        await gps_connections.connect(websocket)
        while True:
            payload = await websocket.receive_json()
            gps_connections.touch(websocket)
            if payload.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                continue
            if current_user.role.value not in {"Admin", "FleetManager", "Driver"}:
                await websocket.send_json({"type": "error", "detail": "You cannot publish GPS locations"})
                continue
            try:
                gps_data = GPSTrackingCreate.model_validate(payload)
                _enforce_vehicle_scope(gps_data.vehicle_id, current_user, db)
            except (ValueError, HTTPException) as error:
                detail = error.detail if isinstance(error, HTTPException) else str(error)
                await websocket.send_json({"type": "error", "detail": detail})
                continue
            location = create_gps_tracking(db, gps_data)
            _refresh_active_trip_eta(location, db)
            await gps_connections.publish(_location_event(location))
    except WebSocketDisconnect:
        pass
    finally:
        gps_connections.disconnect(websocket)
        db.close()


def _distance_meters(latitude: float, longitude: float, zone_latitude: float, zone_longitude: float) -> float:
    """Calculate great-circle distance for geofence checks."""
    earth_radius_m = 6_371_000
    lat_delta = radians(zone_latitude - latitude)
    lon_delta = radians(zone_longitude - longitude)
    value = sin(lat_delta / 2) ** 2 + cos(radians(latitude)) * cos(radians(zone_latitude)) * sin(lon_delta / 2) ** 2
    return earth_radius_m * 2 * asin(sqrt(value))


@router.post("/geofence/{vehicle_id}")
async def check_geofence(
    vehicle_id: UUID,
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    zone_latitude: float = Query(..., ge=-90, le=90),
    zone_longitude: float = Query(..., ge=-180, le=180),
    radius_m: float = Query(100, gt=0, le=100000),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _enforce_vehicle_scope(vehicle_id, current_user, db)
    distance_m = _distance_meters(latitude, longitude, zone_latitude, zone_longitude)
    arrived = distance_m <= radius_m
    event = {"type": "geofence", "vehicle_id": str(vehicle_id), "arrived": arrived, "distance_m": round(distance_m, 2), "radius_m": radius_m}
    if arrived:
        await gps_connections.publish(event)
    return event


@router.get("/history/{vehicle_id}", response_model=list[GPSTrackingOut])
def read_tracking_history(vehicle_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    _enforce_vehicle_scope(vehicle_id, current_user, db)
    return get_tracking_history(db, vehicle_id)


@router.get("/{vehicle_id}", response_model=GPSTrackingOut)
def read_latest_location(vehicle_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    _enforce_vehicle_scope(vehicle_id, current_user, db)
    location = get_latest_location(db, vehicle_id)
    if not location:
        raise HTTPException(status_code=404, detail="GPS location not found")
    return location


@router.get("/", response_model=list[GPSTrackingOut])
def read_latest_locations(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    if current_user.role.value in {"Admin", "FleetManager", "Dispatcher"}:
        return get_latest_locations(db)
    if current_user.role.value == "Driver":
        vehicle_ids = _driver_vehicle_ids(current_user, db)
        return [location for location in get_latest_locations(db) if location.vehicle_id in vehicle_ids]
    raise HTTPException(status_code=403, detail="You do not have access to GPS locations")
