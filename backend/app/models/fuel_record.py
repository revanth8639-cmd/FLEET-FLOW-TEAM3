import uuid
from datetime import datetime

from sqlalchemy import Column, String, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class FuelRecord(Base):
    __tablename__ = "fuel_records"

    fuel_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    vehicle_id = Column(
        UUID(as_uuid=True),
        ForeignKey("vehicles.vehicle_id"),
        nullable=False
    )

    fuel_amount = Column(
        Float,
        nullable=False
    )

    fuel_cost = Column(
        Float,
        nullable=False
    )

    fuel_station = Column(
        String,
        nullable=False
    )

    filled_by = Column(
        String,
        nullable=True
    )

    fuel_date = Column(
        DateTime,
        default=datetime.utcnow
    )

    mileage = Column(Float, nullable=True)
    refill_date = Column(DateTime, nullable=True)
