from pydantic import BaseModel


class DashboardSummary(BaseModel):
    total_vehicles: int
    total_drivers: int
    total_shipments: int
    total_trips: int
    total_maintenance: int
    total_fuel_records: int
    total_notifications: int
    total_attendance: int
    role: str | None = None
    vehicle_statuses: dict[str, int] = {}
    active_shipments: int = 0
    upcoming_maintenance: list[dict] = []
    own_vehicle_id: str | None = None
    own_vehicle_status: str | None = None
    own_active_trip_id: str | None = None
    own_performance: dict[str, float | int] = {}
    vehicle_types: dict[str, int] = {}
    shipment_statuses: dict[str, int] = {}
    fleet_utilization_rate: float = 0
    fuel_monthly: dict[str, float | int] = {}
    maintenance_by_type: dict[str, float | int] = {}
    driver_leaderboard: list[dict] = []
    delayed_shipments: int = 0
    average_delivery_hours: float = 0
    route_modes: dict[str, int] = {}
    eta_accuracy_minutes: float | None = None
    route_performance: dict[str, float | int] = {}
    fleet_utilization_trend: list[dict] = []
    shipment_volume_trend: list[dict] = []
    top_fuel_vehicles: list[dict] = []
    shipment_attention: list[dict] = []
    notification_stats: dict[str, int] = {}
    most_serviced_vehicles: list[dict] = []
    own_recent_trips: list[dict] = []
    own_next_shipment: dict | None = None
    user_registration_trend: list[dict] = []
    vehicle_registration_trend: list[dict] = []
    shipment_delivery_statuses: dict[str, int] = {}
