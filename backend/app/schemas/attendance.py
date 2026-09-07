from uuid import UUID
from datetime import date as calendar_date, datetime

from pydantic import BaseModel, ConfigDict


class AttendanceCreate(BaseModel):
    driver_id: UUID
    check_in: datetime
    check_out: datetime | None = None
    status: str
    date: calendar_date | None = None


class AttendanceUpdate(BaseModel):
    check_in: datetime | None = None
    check_out: datetime | None = None
    status: str | None = None
    date: calendar_date | None = None


class AttendanceOut(BaseModel):
    attendance_id: UUID
    driver_id: UUID
    check_in: datetime
    check_out: datetime | None
    status: str
    date: calendar_date | None = None

    model_config = ConfigDict(from_attributes=True)
