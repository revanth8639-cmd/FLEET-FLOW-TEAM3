from uuid import UUID
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class TripCreate(BaseModel):
    vehicle_id: UUID
    driver_id: UUID
    shipment_id: UUID
    start_location: str
    end_location: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: str = "Scheduled"
    route_type: Optional[str] = "Fastest Route"


class TripUpdate(BaseModel):
    vehicle_id: Optional[UUID] = None
    driver_id: Optional[UUID] = None
    shipment_id: Optional[UUID] = None
    start_location: Optional[str] = None
    end_location: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[str] = None
    distance_km: Optional[float] = None
    actual_distance_km: Optional[float] = None
    duration_minutes: Optional[int] = None
    route_type: Optional[str] = None
    eta: Optional[datetime] = None


class TripOut(BaseModel):
    trip_id: UUID
    vehicle_id: UUID
    driver_id: UUID
    shipment_id: UUID
    start_location: str
    end_location: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    status: str
    distance_km: Optional[float]
    actual_distance_km: Optional[float]
    duration_minutes: Optional[int]
    route_type: Optional[str]
    eta: Optional[datetime]
    remaining_distance_km: Optional[float]

    model_config = ConfigDict(from_attributes=True)
