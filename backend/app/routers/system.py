import os
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.database import get_db
from app.models.job_run import JobRun
from app.models.shipment import Shipment
from app.models.user import User
from app.models.vehicle import Vehicle

router = APIRouter(prefix="/system", tags=["System Monitoring"])


@router.get("/analytics")
def system_analytics(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("Admin")),
):
    """Return Admin analytics for all records or an optional inclusive date range."""
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=400, detail="date_from must be on or before date_to")

    def in_range(column, query):
        if date_from:
            query = query.filter(column >= datetime.combine(date_from, time.min))
        if date_to:
            query = query.filter(column < datetime.combine(date_to + timedelta(days=1), time.min))
        return query

    users = in_range(User.created_at, db.query(User)).all()
    vehicles = in_range(Vehicle.created_at, db.query(Vehicle)).all()
    shipments = in_range(Shipment.created_at, db.query(Shipment)).all()

    def daily_counts(records, field):
        counts = {}
        for record in records:
            timestamp = getattr(record, field, None)
            if timestamp:
                key = timestamp.date().isoformat()
                counts[key] = counts.get(key, 0) + 1
        return [{"date": day, "count": count} for day, count in sorted(counts.items())]

    def status_counts(records):
        counts = {}
        for record in records:
            status = record.status or "Unknown"
            counts[status] = counts.get(status, 0) + 1
        return counts

    return {
        "user_registrations": daily_counts(users, "created_at"),
        "vehicle_registrations": daily_counts(vehicles, "created_at"),
        "shipment_delivery_statuses": status_counts(shipments),
        "fleet_usage_statuses": status_counts(db.query(Vehicle).all()),
    }


@router.get("/health")
def system_health(db: Session = Depends(get_db), current_user=Depends(require_roles("Admin"))):
    redis_status = "unavailable"
    celery_workers = []
    try:
        import redis
        client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), socket_connect_timeout=1)
        client.ping()
        redis_status = "connected"
        client.close()
    except Exception:
        pass
    try:
        from app.celery_app import celery_app
        celery_workers = sorted((celery_app.control.inspect(timeout=1).ping() or {}).keys())
    except Exception:
        pass
    last_runs = {}
    for run in db.query(JobRun).order_by(JobRun.started_at.desc()).limit(20).all():
        if run.task_name not in last_runs:
            last_runs[run.task_name] = {
                "started_at": run.started_at,
                "finished_at": run.finished_at,
                "success": run.success,
                "result": run.result,
            }
    return {"backend": "healthy", "database": "connected", "redis": redis_status, "celery_workers": celery_workers, "celery_ready": bool(celery_workers), "celery_last_runs": last_runs}
