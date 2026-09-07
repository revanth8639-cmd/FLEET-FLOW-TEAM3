from sqlalchemy.orm import Session

from app.models.attendance import Attendance
from app.schemas.attendance import (
    AttendanceCreate,
    AttendanceUpdate,
)


def create_attendance(db: Session, attendance: AttendanceCreate):
    values = attendance.model_dump()
    values["date"] = values.get("date") or values["check_in"].date()
    existing = db.query(Attendance).filter(Attendance.driver_id == values["driver_id"], Attendance.date == values["date"]).first()
    if existing:
        existing.status = values["status"]
        existing.check_in = values["check_in"]
        existing.check_out = values.get("check_out")
        db.commit()
        db.refresh(existing)
        return existing
    db_attendance = Attendance(
        **values
    )

    db.add(db_attendance)
    db.commit()
    db.refresh(db_attendance)

    return db_attendance


def get_attendances(db: Session):
    return db.query(Attendance).all()


def get_attendance(db: Session, attendance_id):
    return db.query(Attendance).filter(
        Attendance.attendance_id == attendance_id
    ).first()


def update_attendance(
    db: Session,
    attendance_id,
    attendance: AttendanceUpdate
):
    db_attendance = get_attendance(db, attendance_id)

    if not db_attendance:
        return None

    for key, value in attendance.model_dump(exclude_unset=True).items():
        setattr(db_attendance, key, value)

    db.commit()
    db.refresh(db_attendance)

    return db_attendance


def delete_attendance(db: Session, attendance_id):
    db_attendance = get_attendance(db, attendance_id)

    if not db_attendance:
        return None

    db.delete(db_attendance)
    db.commit()

    return db_attendance
