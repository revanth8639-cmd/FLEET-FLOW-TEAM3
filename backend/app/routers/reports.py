from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.crud.reports import (
    REPORT_TITLES,
    build_report,
    get_fuel_report,
    get_maintenance_report,
    get_reports_summary,
    get_shipment_report,
    get_trip_report,
    get_vehicle_report,
)
from app.database import get_db
from app.schemas.reports import (
    FuelReport,
    MaintenanceReport,
    ReportResponse,
    ReportsSummary,
    ShipmentReport,
    TripReport,
    VehicleReport,
)
from app.utils.report_exports import build_excel, build_pdf


router = APIRouter(prefix="/reports", tags=["Reports & Analytics"])

REPORT_ACCESS = {
    "Admin": set(REPORT_TITLES),
    "FleetManager": set(REPORT_TITLES),
    "Dispatcher": {"delivery-performance"},
    "Driver": {"driver-performance"},
}


def _check_access(report_type: str, current_user):
    if report_type not in REPORT_TITLES:
        raise HTTPException(status_code=404, detail="Report type not found")
    role = getattr(current_user, "role", None)
    role_name = getattr(role, "value", role)
    allowed = REPORT_ACCESS.get(role_name, set())
    if report_type not in allowed:
        raise HTTPException(status_code=403, detail="Your role cannot access this report")


def _build(report_type: str, date_from: date | None, date_to: date | None, db: Session, current_user):
    _check_access(report_type, current_user)
    try:
        return build_report(report_type, db, date_from, date_to, current_user)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/summary", response_model=ReportsSummary)
def reports_summary(db: Session = Depends(get_db), current_user=Depends(require_roles("Admin", "FleetManager"))):
    return get_reports_summary(db)


@router.get("/shipments", response_model=ShipmentReport)
def shipment_reports(db: Session = Depends(get_db), current_user=Depends(require_roles("Admin", "FleetManager"))):
    return get_shipment_report(db)


@router.get("/trips", response_model=TripReport)
def trip_reports(db: Session = Depends(get_db), current_user=Depends(require_roles("Admin", "FleetManager"))):
    return get_trip_report(db)


@router.get("/vehicles", response_model=VehicleReport)
def vehicle_reports(db: Session = Depends(get_db), current_user=Depends(require_roles("Admin", "FleetManager"))):
    return get_vehicle_report(db)


@router.get("/fuel", response_model=FuelReport)
def fuel_reports(db: Session = Depends(get_db), current_user=Depends(require_roles("Admin", "FleetManager"))):
    return get_fuel_report(db)


@router.get("/maintenance-count", response_model=MaintenanceReport)
def maintenance_reports(db: Session = Depends(get_db), current_user=Depends(require_roles("Admin", "FleetManager"))):
    return get_maintenance_report(db)


@router.get("/{report_type}/export")
def export_report(
    report_type: str,
    format: str = Query("pdf", pattern="^(pdf|xlsx)$"),
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    report = _build(report_type, date_from, date_to, db, current_user)
    try:
        content = build_pdf(report) if format == "pdf" else build_excel(report)
    except ImportError as error:
        library = "reportlab" if format == "pdf" else "openpyxl"
        raise HTTPException(status_code=503, detail=f"{library} is not installed on the server") from error
    suffix = "pdf" if format == "pdf" else "xlsx"
    media_type = "application/pdf" if format == "pdf" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    filename = f"{report_type}-{date_from or 'all'}-to-{date_to or 'all'}.{suffix}"
    return StreamingResponse(content, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/{report_type}", response_model=ReportResponse)
def report_preview(
    report_type: str,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return _build(report_type, date_from, date_to, db, current_user)
