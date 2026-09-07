from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict


class ShipmentReport(BaseModel):
    total_shipments: int


class TripReport(BaseModel):
    total_trips: int


class VehicleReport(BaseModel):
    total_vehicles: int


class FuelReport(BaseModel):
    total_fuel_records: int


class MaintenanceReport(BaseModel):
    total_maintenance: int


class ReportsSummary(BaseModel):
    total_vehicles: int
    total_drivers: int
    total_shipments: int
    total_trips: int
    total_fuel_records: int
    total_maintenance: int
    total_notifications: int
    total_attendance: int


class ReportResponse(BaseModel):
    """Common shape used by report previews and export generation."""

    report_type: str
    title: str
    date_from: date | None
    date_to: date | None
    columns: list[str]
    rows: list[dict[str, Any]]
    summary: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)
