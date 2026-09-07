from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DriverCreate(BaseModel):
    user_id: UUID | None = None
    vehicle_id: UUID | None = None
    name: str
    phone: str
    license_number: str
    status: str = "Available"


class DriverUpdate(BaseModel):
    user_id: UUID | None = None
    vehicle_id: UUID | None = None
    name: str | None = None
    phone: str | None = None
    license_number: str | None = None
    status: str | None = None


class DriverOut(BaseModel):
    driver_id: UUID
    user_id: UUID | None
    vehicle_id: UUID | None
    name: str
    phone: str
    license_number: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
