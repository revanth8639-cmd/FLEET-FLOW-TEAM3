import uuid
from datetime import datetime, timedelta
from math import ceil

from sqlalchemy import Column, String, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class VehicleMaintenance(Base):
    __tablename__ = "vehicle_maintenance"

    maintenance_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    vehicle_id = Column(
        UUID(as_uuid=True),
        ForeignKey("vehicles.vehicle_id"),
        nullable=False
    )

    service_type = Column(
        String,
        nullable=False
    )

    description = Column(
        String,
        nullable=True
    )

    service_date = Column(
        DateTime,
        default=datetime.utcnow
    )

    next_service_date = Column(
        DateTime,
        nullable=True
    )

    cost = Column(
        Float,
        nullable=True
    )

    status = Column(
        String,
        default="Pending"
    )

    @property
    def is_resolved(self) -> bool:
        """Completed and Resolved are both terminal maintenance states."""
        return (self.status or "").strip().lower() in {"completed", "resolved"}

    @property
    def alert_due_date(self) -> datetime | None:
        """Return the fixed five-day maintenance deadline from service start."""
        if self.service_date:
            return self.service_date + timedelta(days=5)
        return self.next_service_date

    @property
    def alert_5_days(self) -> bool:
        """Whether the five-day warning window is currently active."""
        return bool(self.alert_due_date and not self.is_resolved and datetime.utcnow() >= self.alert_due_date - timedelta(days=5))

    @property
    def alert_1_day(self) -> bool:
        """Whether the one-day warning window is currently active."""
        return bool(self.alert_due_date and not self.is_resolved and datetime.utcnow() >= self.alert_due_date - timedelta(days=1))

    @property
    def alert_due(self) -> bool:
        """Whether the service date has passed and still needs resolution."""
        return bool(self.alert_due_date and not self.is_resolved and datetime.utcnow() >= self.alert_due_date)

    @property
    def alert_status(self) -> str | None:
        """Human-readable due status shown alongside the maintenance status."""
        if not self.alert_due_date or self.is_resolved:
            return None
        remaining = self.alert_due_date - datetime.utcnow()
        if remaining.total_seconds() <= 0:
            return "Overdue"
        days = ceil(remaining.total_seconds() / 86400)
        if days <= 1:
            return "Due tomorrow"
        if days <= 5:
            return f"Due in {days} days"
        return None
