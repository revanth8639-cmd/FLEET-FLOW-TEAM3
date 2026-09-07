import uuid
from datetime import date as calendar_date, datetime

from sqlalchemy import Column, Date, DateTime, String, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("driver_id", "date", name="uq_attendance_driver_date"),)

    attendance_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    driver_id = Column(
        UUID(as_uuid=True),
        ForeignKey("drivers.driver_id"),
        nullable=False
    )

    check_in = Column(
        DateTime,
        default=datetime.utcnow
    )

    check_out = Column(
        DateTime,
        nullable=True
    )

    status = Column(
        String,
        nullable=False
    )

    date = Column(
        Date,
        nullable=False,
        default=lambda: datetime.utcnow().date(),
    )
