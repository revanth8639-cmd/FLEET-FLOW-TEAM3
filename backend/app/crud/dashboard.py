from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.vehicle import Vehicle
from app.models.driver import Driver
from app.models.shipment import Shipment
from app.models.trip import Trip
from app.models.maintenance import VehicleMaintenance
from app.models.fuel_record import FuelRecord
from app.models.notification import Notification
from app.models.attendance import Attendance
from app.models.user import User
from app.crud.driver import ensure_driver_profiles


def get_dashboard_summary(db: Session, current_user=None):
    ensure_driver_profiles(db)
    role = getattr(getattr(current_user, "role", None), "value", None)
    driver = db.query(Driver).filter(Driver.user_id == current_user.user_id).first() if role == "Driver" else None
    vehicle_ids = {driver.vehicle_id} if driver and driver.vehicle_id else set()
    vehicles_query = db.query(Vehicle)
    shipments_query = db.query(Shipment)
    trips_query = db.query(Trip)
    maintenance_query = db.query(VehicleMaintenance)
    fuel_query = db.query(FuelRecord)
    attendance_query = db.query(Attendance)
    if driver:
        vehicles_query = vehicles_query.filter(Vehicle.vehicle_id.in_(vehicle_ids)) if vehicle_ids else vehicles_query.filter(False)
        shipments_query = shipments_query.filter(Shipment.driver_id == driver.driver_id)
        trips_query = trips_query.filter(Trip.driver_id == driver.driver_id)
        maintenance_query = maintenance_query.filter(VehicleMaintenance.vehicle_id.in_(vehicle_ids)) if vehicle_ids else maintenance_query.filter(False)
        fuel_query = fuel_query.filter(FuelRecord.vehicle_id.in_(vehicle_ids)) if vehicle_ids else fuel_query.filter(False)
        attendance_query = attendance_query.filter(Attendance.driver_id == driver.driver_id)
    vehicles = vehicles_query.all()
    shipments = shipments_query.all()
    trips = trips_query.all()
    maintenance = sorted(
        maintenance_query.all(),
        key=lambda record: record.next_service_date or record.service_date or datetime.max,
    )
    status_counts = {}
    vehicle_types = {}
    for vehicle in vehicles:
        status_counts[vehicle.status or "Unknown"] = status_counts.get(vehicle.status or "Unknown", 0) + 1
        vehicle_types[vehicle.vehicle_type or "Unknown"] = vehicle_types.get(vehicle.vehicle_type or "Unknown", 0) + 1
    shipment_statuses = {}
    for shipment in shipments:
        shipment_statuses[shipment.status or "Unknown"] = shipment_statuses.get(shipment.status or "Unknown", 0) + 1
    active_shipments = sum(shipment_statuses.get(status, 0) for status in ("Assigned", "In Transit"))
    now = datetime.utcnow()
    upcoming = []
    for record in maintenance:
        if record.is_resolved or not record.alert_status:
            continue
        upcoming.append({"maintenance_id": str(record.maintenance_id), "vehicle_id": str(record.vehicle_id), "service_type": record.service_type, "status": record.alert_status})
    own_performance = {}
    own_recent_trips = []
    own_next_shipment = None
    if driver:
        shipment_by_id = {shipment.shipment_id: shipment for shipment in shipments}
        completed = [trip for trip in trips if (trip.status or "").lower() == "completed"]
        delivered = [trip for trip in completed if trip.end_time]
        attendance_records = attendance_query.all()
        present_days = sum(1 for record in attendance_records if (record.status or "").lower() == "present")
        own_performance = {"trips_completed": len(completed), "trips_total": len(trips), "on_time_rate": 0, "attendance_days": len(attendance_records), "present_days": present_days, "attendance_rate": round(present_days / len(attendance_records) * 100, 2) if attendance_records else 0}
        if delivered:
            on_time = [
                trip
                for trip in delivered
                if shipment_by_id.get(trip.shipment_id)
                and shipment_by_id[trip.shipment_id].expected_delivery_at
                and trip.end_time <= shipment_by_id[trip.shipment_id].expected_delivery_at
            ]
            own_performance["on_time_rate"] = round(len(on_time) / len(delivered) * 100, 2)
        own_recent_trips = [
            {"trip_id": str(trip.trip_id), "status": trip.status, "end_time": trip.end_time.isoformat() if trip.end_time else None}
            for trip in sorted(trips, key=lambda item: item.end_time or item.start_time or datetime.min, reverse=True)[:5]
        ]
        next_shipments = [shipment for shipment in shipments if (shipment.status or "").lower() in {"assigned", "created", "in transit"}]
        if next_shipments:
            shipment = next_shipments[0]
            own_next_shipment = {"shipment_id": str(shipment.shipment_id), "tracking_number": shipment.tracking_number, "status": shipment.status}
    active_trip = trips_query.filter(Trip.status == "In Progress").first() if driver else None
    own_vehicle = vehicles[0] if driver and vehicles else None
    in_use = sum(status_counts.get(status, 0) for status in ("Assigned", "In Transit"))
    monthly_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    fuel_month = [record for record in fuel_query.all() if record.fuel_date and record.fuel_date >= monthly_start]
    fuel_litres = sum(record.fuel_amount or 0 for record in fuel_month)
    fuel_cost = sum(record.fuel_cost or 0 for record in fuel_month)
    fuel_by_vehicle = defaultdict(float)
    for record in fuel_month:
        fuel_by_vehicle[record.vehicle_id] += record.fuel_cost or 0
    top_fuel_vehicles = []
    for vehicle_id, cost in sorted(fuel_by_vehicle.items(), key=lambda item: item[1], reverse=True)[:5]:
        vehicle = next((item for item in vehicles if item.vehicle_id == vehicle_id), None)
        top_fuel_vehicles.append({"vehicle_id": str(vehicle_id), "vehicle": vehicle.registration_number if vehicle else "Unknown vehicle", "cost": round(cost, 2)})
    distance = sum(trip.actual_distance_km or trip.distance_km or 0 for trip in trips if trip.end_time and trip.end_time >= monthly_start)
    maintenance_by_type = defaultdict(float)
    maintenance_by_vehicle = defaultdict(int)
    for record in maintenance:
        maintenance_by_type[record.service_type or "Unknown"] += record.cost or 0
        maintenance_by_vehicle[record.vehicle_id] += 1
    most_serviced_vehicles = []
    for vehicle_id, count in sorted(maintenance_by_vehicle.items(), key=lambda item: item[1], reverse=True)[:5]:
        vehicle = next((item for item in vehicles if item.vehicle_id == vehicle_id), None)
        most_serviced_vehicles.append({"vehicle_id": str(vehicle_id), "vehicle": vehicle.registration_number if vehicle else "Unknown vehicle", "records": count})
    shipment_attention = [
        {"shipment_id": str(shipment.shipment_id), "tracking_number": shipment.tracking_number, "status": shipment.status}
        for shipment in shipments if (shipment.status or "").lower() in {"delayed", "cancelled"}
    ]
    driver_leaderboard = []
    if role in {"Admin", "FleetManager"}:
        all_shipments = {shipment.shipment_id: shipment for shipment in db.query(Shipment).all()}
        all_attendance = db.query(Attendance).order_by(Attendance.date.desc(), Attendance.check_in.desc()).all()
        for item in db.query(Driver).all():
            driver_trips = [trip for trip in db.query(Trip).filter(Trip.driver_id == item.driver_id).all() if (trip.status or "").lower() == "completed"]
            delivered = [trip for trip in driver_trips if trip.end_time]
            on_time = [trip for trip in delivered if all_shipments.get(trip.shipment_id) and all_shipments[trip.shipment_id].expected_delivery_at and trip.end_time <= all_shipments[trip.shipment_id].expected_delivery_at]
            attendance = [record for record in all_attendance if record.driver_id == item.driver_id]
            present = [record for record in attendance if (record.status or "").lower() == "present"]
            driver_leaderboard.append({"driver_id": str(item.driver_id), "driver": item.name, "license_number": item.license_number or "-", "status": item.status or "Available", "trips_completed": len(driver_trips), "on_time_rate": round(len(on_time) / len(delivered) * 100, 2) if delivered else 0, "attendance_rate": round(len(present) / len(attendance) * 100, 2) if attendance else 0})
        driver_leaderboard.sort(key=lambda item: (-item["trips_completed"], item["driver"].lower()))
    notification_rows = db.query(Notification).filter(Notification.user_id == current_user.user_id).all() if current_user else db.query(Notification).all()
    notification_stats = {
        "total": len(notification_rows),
        "unread": sum(1 for notification in notification_rows if not notification.is_read),
        "last_24_hours": sum(1 for notification in notification_rows if notification.created_at and notification.created_at >= now - timedelta(hours=24)),
    }
    delivery_durations = [(trip.end_time - shipment.created_at).total_seconds() / 3600 for trip in trips for shipment in shipments if trip.shipment_id == shipment.shipment_id and trip.end_time and shipment.created_at]
    eta_errors = [abs((trip.end_time - trip.eta).total_seconds()) / 60 for trip in trips if trip.end_time and trip.eta]
    route_modes = {}
    for trip in trips:
        if trip.route_type:
            route_modes[trip.route_type] = route_modes.get(trip.route_type, 0) + 1
    completed_trips = [trip for trip in trips if trip.end_time and trip.start_time]
    actual_distances = [trip.actual_distance_km for trip in completed_trips if trip.actual_distance_km is not None]
    estimated_distances = [trip.distance_km for trip in completed_trips if trip.distance_km is not None]
    actual_durations = [
        (trip.end_time - trip.start_time).total_seconds() / 60
        for trip in completed_trips
    ]
    estimated_durations = [trip.duration_minutes for trip in completed_trips if trip.duration_minutes is not None]
    route_performance = {
        "actual_distance_km": round(sum(actual_distances) / len(actual_distances), 2) if actual_distances else 0,
        "estimated_distance_km": round(sum(estimated_distances) / len(estimated_distances), 2) if estimated_distances else 0,
        "actual_duration_minutes": round(sum(actual_durations) / len(actual_durations), 2) if actual_durations else 0,
        "estimated_duration_minutes": round(sum(estimated_durations) / len(estimated_durations), 2) if estimated_durations else 0,
    }
    fleet_utilization_trend = []
    shipment_volume_trend = []
    user_registration_trend = []
    vehicle_registration_trend = []
    for offset in range(6, -1, -1):
        day = (now - timedelta(days=offset)).date()
        day_trips = [trip for trip in trips if trip.start_time and trip.start_time.date() == day]
        day_shipments = [shipment for shipment in shipments if shipment.created_at and shipment.created_at.date() == day]
        active_vehicle_ids = {trip.vehicle_id for trip in day_trips}
        fleet_utilization_trend.append({"date": day.isoformat(), "rate": round(len(active_vehicle_ids) / len(vehicles) * 100, 2) if vehicles else 0})
        shipment_volume_trend.append({"date": day.isoformat(), "count": len(day_shipments)})
        day_start = datetime.combine(day, datetime.min.time())
        day_end = day_start + timedelta(days=1)
        user_registration_trend.append({"date": day.isoformat(), "count": db.query(User).filter(User.created_at >= day_start, User.created_at < day_end).count()})
        vehicle_registration_trend.append({"date": day.isoformat(), "count": db.query(Vehicle).filter(Vehicle.created_at >= day_start, Vehicle.created_at < day_end).count()})
    return {
        "total_vehicles": len(vehicles),
        "total_drivers": db.query(Driver).filter(Driver.driver_id == driver.driver_id).count() if driver else db.query(Driver).count(),
        "total_shipments": shipments_query.count(),
        "total_trips": trips_query.count(),
        "total_maintenance": maintenance_query.count(),
        "total_fuel_records": fuel_query.count(),
        "total_notifications": db.query(Notification).filter(Notification.user_id == current_user.user_id).count() if current_user else db.query(Notification).count(),
        "total_attendance": attendance_query.count(),
        "role": role,
        "vehicle_statuses": status_counts,
        "active_shipments": active_shipments,
        "upcoming_maintenance": upcoming,
        "own_vehicle_id": str(own_vehicle.vehicle_id) if own_vehicle else None,
        "own_vehicle_status": own_vehicle.status if own_vehicle else None,
        "own_active_trip_id": str(active_trip.trip_id) if active_trip else None,
        "own_performance": own_performance,
        "vehicle_types": vehicle_types,
        "shipment_statuses": shipment_statuses,
        "fleet_utilization_rate": round(in_use / len(vehicles) * 100, 2) if vehicles else 0,
        "fuel_monthly": {"cost": round(fuel_cost, 2), "litres": round(fuel_litres, 2), "distance_km": round(distance, 2), "efficiency_km_per_litre": round(distance / fuel_litres, 2) if fuel_litres else 0},
        "maintenance_by_type": {key: round(value, 2) for key, value in maintenance_by_type.items()},
        "driver_leaderboard": driver_leaderboard[:10],
        "delayed_shipments": shipment_statuses.get("Delayed", 0),
        "average_delivery_hours": round(sum(delivery_durations) / len(delivery_durations), 2) if delivery_durations else 0,
        "route_modes": route_modes,
        "eta_accuracy_minutes": round(sum(eta_errors) / len(eta_errors), 2) if eta_errors else None,
        "route_performance": route_performance,
        "fleet_utilization_trend": fleet_utilization_trend,
        "shipment_volume_trend": shipment_volume_trend,
        "top_fuel_vehicles": top_fuel_vehicles,
        "shipment_attention": shipment_attention,
        "notification_stats": notification_stats,
        "most_serviced_vehicles": most_serviced_vehicles,
        "own_recent_trips": own_recent_trips,
        "own_next_shipment": own_next_shipment,
        "user_registration_trend": user_registration_trend,
        "vehicle_registration_trend": vehicle_registration_trend,
        "shipment_delivery_statuses": shipment_statuses,
    }
