"""Scheduled delayed-shipment checks."""

import logging
from datetime import datetime, timedelta

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.shipment import Shipment
from app.models.driver import Driver
from app.models.user import User
from app.models.user import RoleEnum
from app.crud.notification import add_notifications
from app.crud.job_run import start_job, finish_job


logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.shipments.check_delayed_shipments")
def check_delayed_shipments() -> str:
    """Mark shipments that have been in transit for over 24 hours as delayed."""
    db = SessionLocal()
    try:
        run = start_job(db, "check_delayed_shipments")
        cutoff = datetime.utcnow() - timedelta(hours=24)
        overdue = (
            db.query(Shipment)
            .filter(Shipment.status == "In Transit", Shipment.created_at <= cutoff)
            .all()
        )
        for shipment in overdue:
            shipment.status = "Delayed"
            recipient_ids = [
                user.user_id
                for user in db.query(User).filter(User.role.in_([RoleEnum.Admin, RoleEnum.FleetManager, RoleEnum.Dispatcher])).all()
            ]
            if shipment.driver_id:
                driver = db.query(Driver).filter(Driver.driver_id == shipment.driver_id).first()
                if driver:
                    recipient_ids.extend(
                        user_id for user_id, in db.query(User.user_id).filter(User.user_id == driver.user_id).all()
                    )
            add_notifications(
                db,
                recipient_ids,
                "Shipment delayed",
                f"Shipment {shipment.tracking_number} has been delayed after 24 hours in transit.",
                "shipment",
            )
            logger.warning(
                "[SHIPMENT ALERT] %s marked as Delayed", shipment.tracking_number
            )
        finish_job(db, run, success=True, result=f"Checked shipments - {len(overdue)} marked Delayed")
        return f"Checked shipments — {len(overdue)} marked Delayed"
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
