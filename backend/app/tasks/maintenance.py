"""Scheduled maintenance alerts for Admin and Fleet Manager accounts."""
import logging
from datetime import datetime, timedelta

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.maintenance import VehicleMaintenance
from app.models.notification import Notification
from app.models.user import RoleEnum, User
from app.models.driver import Driver
from app.crud.job_run import start_job, finish_job

logger = logging.getLogger(__name__)
RESOLVED_STATUSES = {"completed", "resolved"}


def _notification_exists(db, user_id, title) -> bool:
    return db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.title == title,
    ).first() is not None


@celery_app.task(name="app.tasks.maintenance.check_maintenance_alerts")
def check_maintenance_alerts() -> str:
    db = SessionLocal()
    try:
        run = start_job(db, "check_maintenance_alerts")
        now = datetime.utcnow()
        records = db.query(VehicleMaintenance).all()
        recipients = db.query(User).filter(User.role.in_([RoleEnum.Admin, RoleEnum.FleetManager])).all()
        drivers = db.query(Driver).all()
        driver_users = {driver.vehicle_id: driver.user_id for driver in drivers if driver.vehicle_id and driver.user_id}
        created = 0
        for record in records:
            if (record.status or "").strip().lower() in RESOLVED_STATUSES:
                continue
            service_date = record.alert_due_date
            if not service_date:
                continue
            if service_date > now + timedelta(days=5):
                continue

            # Advance warnings are emitted once. Once overdue, a new reminder
            # is emitted each UTC day until the record is resolved.
            if now >= service_date:
                kind = "Due"
                title = f"Due maintenance: {record.maintenance_id} ({now.date().isoformat()})"
            elif now >= service_date - timedelta(days=1):
                kind = "1-day reminder"
                title = f"1-day maintenance reminder: {record.maintenance_id}"
            else:
                kind = "5-day reminder"
                title = f"5-day maintenance reminder: {record.maintenance_id}"
            if kind == "5-day reminder":
                message = f"Vehicle {record.vehicle_id} is due for {record.service_type} maintenance in 5 days ({service_date.isoformat()})."
            elif kind == "1-day reminder":
                message = f"Vehicle {record.vehicle_id} is due for {record.service_type} maintenance tomorrow ({service_date.isoformat()})."
            else:
                message = f"Vehicle {record.vehicle_id} maintenance for {record.service_type} is overdue (due {service_date.isoformat()})."
            target_users = [user.user_id for user in recipients]
            driver_user_id = driver_users.get(record.vehicle_id)
            if driver_user_id:
                target_users.append(driver_user_id)
            for user_id in set(target_users):
                if not _notification_exists(db, user_id, title):
                    db.add(Notification(user_id=user_id, title=title, message=message, type="maintenance"))
                    created += 1
            logger.warning("[MAINTENANCE ALERT] %s (%s)", message, kind)
        finish_job(db, run, success=True, result=f"Checked {len(records)} record(s); created {created} alert(s)")
        return f"Checked {len(records)} record(s); created {created} alert(s)"
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
