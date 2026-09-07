from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MaintenanceCreate(BaseModel):
    vehicle_id: UUID
    service_type: str
    description: str | None = None
    service_date: datetime | None = None
    next_service_date: datetime | None = None
    cost: float | None = None
    status: str = "Pending"


class MaintenanceUpdate(BaseModel):
    service_type: str | None = None
    description: str | None = None
    service_date: datetime | None = None
    next_service_date: datetime | None = None
    cost: float | None = None
    status: str | None = None


class MaintenanceOut(BaseModel):
    maintenance_id: UUID
    vehicle_id: UUID
    service_type: str
    description: str | None
    service_date: datetime
    next_service_date: datetime | None
    alert_due_date: datetime | None
    cost: float | None
    status: str
    alert_5_days: bool
    alert_1_day: bool
    alert_due: bool
    alert_status: str | None

    model_config = ConfigDict(from_attributes=True)
