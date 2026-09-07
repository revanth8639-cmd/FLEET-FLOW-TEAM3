import uuid
from datetime import datetime

from sqlalchemy import Column, Float, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Shipment(Base):
    __tablename__ = "shipments"

    shipment_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    vehicle_id = Column(
        UUID(as_uuid=True),
        ForeignKey("vehicles.vehicle_id"),
        nullable=True
    )

    driver_id = Column(
        UUID(as_uuid=True),
        ForeignKey("drivers.driver_id"),
        nullable=True
    )

    tracking_number = Column(String, unique=True, nullable=False)
    customer_name = Column(String, nullable=True, index=True)
    shipment_weight = Column(Float, nullable=True)

    source = Column(String, nullable=False)

    destination = Column(String, nullable=False)

    status = Column(String, default="Created")

    eta = Column(String, nullable=True)
    expected_delivery_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
