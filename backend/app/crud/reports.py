from collections import defaultdict
from datetime import date, datetime, time

from sqlalchemy.orm import Session

from app.models.attendance import Attendance
from app.models.driver import Driver
from app.models.fuel_record import FuelRecord
from app.models.maintenance import VehicleMaintenance
from app.models.notification import Notification
from app.models.shipment import Shipment
from app.models.trip import Trip
from app.models.user import User
from app.models.vehicle import Vehicle


REPORT_TITLES = {
    "fleet-utilization": "Fleet Utilization Report",
    "fuel-consumption": "Fuel Consumption Report",
    "driver-performance": "Driver Performance Report",
    "delivery-performance": "Delivery Performance Report",
    "maintenance": "Maintenance Report",
}


def _range_bounds(date_from: date | None, date_to: date | None):
    if date_from and date_to and date_from > date_to:
        raise ValueError("date_from must be on or before date_to")
    start = datetime.combine(date_from, time.min) if date_from else None
    end = datetime.combine(date_to, time.max) if date_to else None
    return start, end


def _as_datetime(value):
    """Normalize date-like values before comparing them with report bounds."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    if isinstance(value, date):
        return datetime.combine(value, time.min)
    return None


def _in_range(value, start, end) -> bool:
    # No selected dates means the complete report, including legacy rows that
    # do not have a timestamp populated yet.
    if start is None and end is None:
        return True
    value = _as_datetime(value)
    return bool(value and (start is None or value >= start) and (end is None or value <= end))


def _any_in_range(values, start, end) -> bool:
    return any(_in_range(value, start, end) for value in values)


def _maintenance_in_range(record, start, end) -> bool:
    """Match a maintenance row by either of its relevant service dates."""
    return any(
        _in_range(value, start, end)
        for value in (record.service_date, record.next_service_date, record.alert_due_date)
    )


def _vehicle_name(vehicle):
    return vehicle.registration_number if vehicle else "Unknown vehicle"


def _driver_name(driver):
    return driver.name if driver else "Unknown driver"


def _role_name(current_user) -> str:
    role = getattr(current_user, "role", None)
    return getattr(role, "value", role) or ""


def _base(report_type, date_from, date_to, columns, rows, summary):
    return {
        "report_type": report_type,
        "title": REPORT_TITLES[report_type],
        "date_from": date_from,
        "date_to": date_to,
        "columns": columns,
        "rows": rows,
        "summary": summary,
    }


def _driver_scope(db: Session, current_user: User):
    if _role_name(current_user) != "Driver":
        return None
    return db.query(Driver).filter(Driver.user_id == current_user.user_id).first()


def build_fleet_utilization(db: Session, date_from, date_to, current_user):
    start, end = _range_bounds(date_from, date_to)
    vehicles = db.query(Vehicle).all()
    trips = [trip for trip in db.query(Trip).all() if _any_in_range((trip.start_time, trip.end_time), start, end)]
    trip_counts = defaultdict(int)
    for trip in trips:
        trip_counts[trip.vehicle_id] += 1
    breakdown = defaultdict(lambda: {"vehicles": 0, "trips": 0})
    for vehicle in vehicles:
        status = vehicle.status or "Unknown"
        breakdown[status]["vehicles"] += 1
        breakdown[status]["trips"] += trip_counts[vehicle.vehicle_id]
    rows = [{"status": status, "vehicles": values["vehicles"], "trips": values["trips"]} for status, values in sorted(breakdown.items())]
    used = sum(1 for vehicle in vehicles if trip_counts[vehicle.vehicle_id])
    return _base("fleet-utilization", date_from, date_to, ["status", "vehicles", "trips"], rows, {
        "total_vehicles": len(vehicles),
        "vehicles_used": used,
        "utilization_rate": round((used / len(vehicles)) * 100, 2) if vehicles else 0,
    })


def build_fuel_consumption(db: Session, date_from, date_to, current_user):
    start, end = _range_bounds(date_from, date_to)
    records = [record for record in db.query(FuelRecord).all() if _any_in_range((record.fuel_date, record.refill_date), start, end)]
    trips = [trip for trip in db.query(Trip).all() if _any_in_range((trip.start_time, trip.end_time), start, end)]
    vehicles = {vehicle.vehicle_id: vehicle for vehicle in db.query(Vehicle).all()}
    distance_by_vehicle = defaultdict(float)
    for trip in trips:
        distance_by_vehicle[trip.vehicle_id] += trip.actual_distance_km or trip.distance_km or 0
    grouped = defaultdict(lambda: {"records": 0, "litres": 0.0, "cost": 0.0})
    for record in records:
        grouped[record.vehicle_id]["records"] += 1
        grouped[record.vehicle_id]["litres"] += record.fuel_amount or 0
        grouped[record.vehicle_id]["cost"] += record.fuel_cost or 0
    rows = []
    for vehicle_id, values in grouped.items():
        rows.append({
            "vehicle": _vehicle_name(vehicles.get(vehicle_id)),
            "fuel_records": values["records"],
            "litres": round(values["litres"], 2),
            "total_cost": round(values["cost"], 2),
            "cost_per_litre": round(values["cost"] / values["litres"], 2) if values["litres"] else 0,
            "distance_km": round(distance_by_vehicle[vehicle_id], 2),
            "efficiency_km_per_litre": round(distance_by_vehicle[vehicle_id] / values["litres"], 2) if values["litres"] else 0,
        })
    return _base("fuel-consumption", date_from, date_to, ["vehicle", "fuel_records", "litres", "total_cost", "cost_per_litre", "distance_km", "efficiency_km_per_litre"], rows, {
        "fuel_records": len(records),
        "litres": round(sum(row["litres"] for row in rows), 2),
        "total_cost": round(sum(row["total_cost"] for row in rows), 2),
        "distance_km": round(sum(row["distance_km"] for row in rows), 2),
        "efficiency_km_per_litre": round(sum(row["distance_km"] for row in rows) / sum(row["litres"] for row in rows), 2) if sum(row["litres"] for row in rows) else 0,
    })


def build_driver_performance(db: Session, date_from, date_to, current_user):
    start, end = _range_bounds(date_from, date_to)
    scoped_driver = _driver_scope(db, current_user)
    drivers = [scoped_driver] if scoped_driver else db.query(Driver).all()
    drivers = [driver for driver in drivers if driver]
    shipments = {shipment.shipment_id: shipment for shipment in db.query(Shipment).all()}
    all_trips = [trip for trip in db.query(Trip).all() if _any_in_range((trip.end_time, trip.start_time), start, end)]
    all_attendance = [record for record in db.query(Attendance).all() if _in_range(record.date, start, end)]
    rows = []
    for driver in drivers:
        completed = [trip for trip in all_trips if trip.driver_id == driver.driver_id and (trip.status or "").lower() == "completed"]
        on_time = [trip for trip in completed if shipments.get(trip.shipment_id) and shipments[trip.shipment_id].expected_delivery_at and trip.end_time and trip.end_time <= shipments[trip.shipment_id].expected_delivery_at]
        attendance = [record for record in all_attendance if record.driver_id == driver.driver_id]
        present = [record for record in attendance if (record.status or "").lower() == "present"]
        rows.append({
            "driver": _driver_name(driver),
            "trips_completed": len(completed),
            "on_time_trips": len(on_time),
            "on_time_rate": round((len(on_time) / len(completed)) * 100, 2) if completed else 0,
            "attendance_days": len(attendance),
            "present_days": len(present),
            "attendance_rate": round((len(present) / len(attendance)) * 100, 2) if attendance else 0,
        })
    return _base("driver-performance", date_from, date_to, ["driver", "trips_completed", "on_time_trips", "on_time_rate", "attendance_days", "present_days", "attendance_rate"], rows, {
        "drivers": len(rows),
        "trips_completed": sum(row["trips_completed"] for row in rows),
        "average_on_time_rate": round(sum(row["on_time_rate"] for row in rows) / len(rows), 2) if rows else 0,
    })


def build_delivery_performance(db: Session, date_from, date_to, current_user):
    start, end = _range_bounds(date_from, date_to)
    trips = {trip.shipment_id: trip for trip in db.query(Trip).all()}
    shipments = [
        shipment for shipment in db.query(Shipment).all()
        if _any_in_range((shipment.created_at, trips.get(shipment.shipment_id).end_time if trips.get(shipment.shipment_id) else None), start, end)
    ]
    completed = delayed = on_time = 0
    delivery_hours = []
    for shipment in shipments:
        trip = trips.get(shipment.shipment_id)
        is_completed = (shipment.status or "").lower() in {"delivered", "completed"} or bool(trip and trip.end_time)
        if not is_completed:
            continue
        completed += 1
        if (shipment.status or "").lower() == "delayed":
            delayed += 1
        elif trip and trip.end_time and shipment.expected_delivery_at and trip.end_time > shipment.expected_delivery_at:
            delayed += 1
        elif trip and trip.end_time and shipment.expected_delivery_at and trip.end_time <= shipment.expected_delivery_at:
            on_time += 1
        if trip and trip.end_time and shipment.created_at:
            delivery_hours.append(max(0, (trip.end_time - shipment.created_at).total_seconds() / 3600))
    rows = [
        {"result": "On time", "shipments": on_time},
        {"result": "Delayed", "shipments": delayed},
        {"result": "Not delivered", "shipments": max(0, len(shipments) - completed)},
    ]
    return _base("delivery-performance", date_from, date_to, ["result", "shipments"], rows, {
        "total_shipments": len(shipments),
        "delivered": completed,
        "on_time": on_time,
        "delayed": delayed,
        "average_delivery_hours": round(sum(delivery_hours) / len(delivery_hours), 2) if delivery_hours else 0,
    })


def build_maintenance_report(db: Session, date_from, date_to, current_user):
    start, end = _range_bounds(date_from, date_to)
    records = [record for record in db.query(VehicleMaintenance).all() if _maintenance_in_range(record, start, end)]
    vehicles = {vehicle.vehicle_id: vehicle for vehicle in db.query(Vehicle).all()}
    grouped = defaultdict(lambda: {"records": 0, "cost": 0.0, "types": defaultdict(int), "upcoming": 0, "overdue": 0})
    now = datetime.utcnow()
    for record in records:
        item = grouped[record.vehicle_id]
        item["records"] += 1
        item["cost"] += record.cost or 0
        item["types"][record.service_type or "Unknown"] += 1
        due_date = _as_datetime(record.alert_due_date)
        if not record.is_resolved and due_date:
            if due_date < now:
                item["overdue"] += 1
            else:
                item["upcoming"] += 1
    rows = [{
        "vehicle": _vehicle_name(vehicles.get(vehicle_id)),
        "maintenance_records": values["records"],
        "total_cost": round(values["cost"], 2),
        "maintenance_types": ", ".join(f"{key} ({count})" for key, count in sorted(values["types"].items())),
        "upcoming": values["upcoming"],
        "overdue": values["overdue"],
    } for vehicle_id, values in grouped.items()]
    frequency = defaultdict(int)
    for record in records:
        frequency[record.service_type or "Unknown"] += 1
    upcoming_overdue = []
    for record in records:
        due_date = _as_datetime(record.alert_due_date)
        if not record.is_resolved and due_date:
            upcoming_overdue.append({
                "vehicle": _vehicle_name(vehicles.get(record.vehicle_id)),
                "service_type": record.service_type or "Unknown",
                "due_date": due_date.isoformat(),
                "status": "Overdue" if due_date < now else "Upcoming",
            })
    return _base("maintenance", date_from, date_to, ["vehicle", "maintenance_records", "total_cost", "maintenance_types", "upcoming", "overdue"], rows, {
        "maintenance_records": len(records),
        "total_cost": round(sum(row["total_cost"] for row in rows), 2),
        "frequency_by_type": dict(sorted(frequency.items())),
        "upcoming_overdue": upcoming_overdue,
    })


BUILDERS = {
    "fleet-utilization": build_fleet_utilization,
    "fuel-consumption": build_fuel_consumption,
    "driver-performance": build_driver_performance,
    "delivery-performance": build_delivery_performance,
    "maintenance": build_maintenance_report,
}


def build_report(report_type, db, date_from, date_to, current_user):
    try:
        builder = BUILDERS[report_type]
    except KeyError as error:
        raise ValueError(f"Unknown report type: {report_type}") from error
    return builder(db, date_from, date_to, current_user)


# Legacy count endpoints retained for existing clients.
def get_reports_summary(db: Session):
    return {
        "total_vehicles": db.query(Vehicle).count(),
        "total_drivers": db.query(Driver).count(),
        "total_shipments": db.query(Shipment).count(),
        "total_trips": db.query(Trip).count(),
        "total_fuel_records": db.query(FuelRecord).count(),
        "total_maintenance": db.query(VehicleMaintenance).count(),
        "total_notifications": db.query(Notification).count(),
        "total_attendance": db.query(Attendance).count(),
    }


def get_shipment_report(db: Session):
    return {"total_shipments": db.query(Shipment).count()}


def get_trip_report(db: Session):
    return {"total_trips": db.query(Trip).count()}


def get_vehicle_report(db: Session):
    return {"total_vehicles": db.query(Vehicle).count()}


def get_fuel_report(db: Session):
    return {"total_fuel_records": db.query(FuelRecord).count()}


def get_maintenance_report(db: Session):
    return {"total_maintenance": db.query(VehicleMaintenance).count()}
