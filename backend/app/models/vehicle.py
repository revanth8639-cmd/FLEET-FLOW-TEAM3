import uuid
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Vehicle(Base):
    __tablename__ = "vehicles"

    vehicle_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    registration_number = Column(
        String,
        unique=True,
        nullable=False
    )

    vehicle_type = Column(
        String,
        nullable=False
    )

    capacity = Column(
        String,
        nullable=False
    )

    fuel_type = Column(
        String,
        nullable=False
    )

    status = Column(
        String,
        default="Available"
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    brand = Column(String, nullable=True)
    model = Column(String, nullable=True)
    manufacture_year = Column(Integer, nullable=True)
    assigned_driver_id = Column(UUID(as_uuid=True), ForeignKey("drivers.driver_id"), nullable=True, unique=True)
