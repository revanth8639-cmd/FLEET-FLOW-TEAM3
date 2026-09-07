import uuid
from datetime import datetime

from sqlalchemy import Column, Float, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Trip(Base):
    __tablename__ = "trips"

    trip_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    vehicle_id = Column(
        UUID(as_uuid=True),
        ForeignKey("vehicles.vehicle_id"),
        nullable=False
    )

    driver_id = Column(
        UUID(as_uuid=True),
        ForeignKey("drivers.driver_id"),
        nullable=False
    )

    shipment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("shipments.shipment_id"),
        nullable=False
    )

    start_location = Column(
        String,
        nullable=False
    )

    end_location = Column(
        String,
        nullable=False
    )

    start_time = Column(
        DateTime,
        default=datetime.utcnow
    )

    end_time = Column(
        DateTime,
        nullable=True
    )

    status = Column(
        String,
        default="Scheduled"
    )

    distance_km = Column(Float, nullable=True)
    actual_distance_km = Column(Float, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    route_type = Column(String, nullable=True)
    eta = Column(DateTime, nullable=True)
    remaining_distance_km = Column(Float, nullable=True)
