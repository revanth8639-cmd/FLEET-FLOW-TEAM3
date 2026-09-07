from uuid import UUID

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_current_driver, get_current_user, require_roles
from app.models.attendance import Attendance

from app.schemas.attendance import (
    AttendanceCreate,
    AttendanceUpdate,
    AttendanceOut,
)

from app.crud.attendance import (
    create_attendance,
    get_attendances,
    get_attendance,
    update_attendance,
    delete_attendance,
)

router = APIRouter(
    prefix="/attendance",
    tags=["Attendance"]
)


@router.post("/", response_model=AttendanceOut)
def create_new_attendance(
    attendance: AttendanceCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role.value not in {"Admin", "FleetManager"}:
        raise HTTPException(status_code=403, detail="You do not have permission to create attendance")
    return create_attendance(db, attendance)


@router.get("/", response_model=list[AttendanceOut])
def read_attendances(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=400, detail="date_from must be on or before date_to")
    records = get_attendances(db)
    records = [
        record for record in records
        if (not date_from or record.date >= date_from)
        and (not date_to or record.date <= date_to)
    ]
    if current_user.role.value in {"Admin", "FleetManager", "Dispatcher"}:
        return records
    if current_user.role.value == "Driver":
        driver = get_current_driver(current_user, db)
        return [record for record in records if record.driver_id == driver.driver_id]
    raise HTTPException(status_code=403, detail="You do not have access to attendance")


@router.get("/{attendance_id}", response_model=AttendanceOut)
def read_attendance(
    attendance_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    attendance = get_attendance(
        db,
        attendance_id
    )

    if not attendance:
        raise HTTPException(
            status_code=404,
            detail="Attendance record not found"
        )

    if current_user.role.value == "Driver" and attendance.driver_id != get_current_driver(current_user, db).driver_id:
        raise HTTPException(status_code=403, detail="You can view only your own attendance")
    if current_user.role.value not in {"Admin", "FleetManager", "Driver"}:
        raise HTTPException(status_code=403, detail="You do not have access to attendance")
    return attendance


@router.put("/{attendance_id}", response_model=AttendanceOut)
def update_existing_attendance(
    attendance_id: UUID,
    attendance: AttendanceUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("Admin", "FleetManager")),
):
    updated = update_attendance(
        db,
        attendance_id,
        attendance
    )

    if not updated:
        raise HTTPException(
            status_code=404,
            detail="Attendance record not found"
        )

    return updated


@router.delete("/{attendance_id}")
def delete_existing_attendance(
    attendance_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("Admin")),
):
    deleted = delete_attendance(
        db,
        attendance_id
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Attendance record not found"
        )

    return {
        "message": "Attendance deleted successfully"
    }
