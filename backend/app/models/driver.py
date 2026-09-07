import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Driver(Base):
    __tablename__ = "drivers"

    driver_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id"),
        unique=True
    )

    # A persistent assignment is required to scope Driver access to their
    # own vehicle, GPS data, fuel records, and maintenance alerts.
    vehicle_id = Column(
        UUID(as_uuid=True),
        ForeignKey("vehicles.vehicle_id"),
        unique=True,
        nullable=True,
    )

    name = Column(
        String,
        nullable=False
    )

    phone = Column(
        String,
        nullable=False
    )

    license_number = Column(
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
