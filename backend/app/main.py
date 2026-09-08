from pathlib import Path
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.security import validate_production_security
import app.models
from app.routers import auth
from app.routers import shipment
from app.routers import gps_tracking
from app.routers import vehicle
from app.routers import trip
from app.routers import driver
from app.routers import maintenance
from app.routers import fuel_record
from app.routers import notification
from app.routers import attendance
from app.routers import dashboard
from app.routers import reports
from app.routers import leave_request
from app.routers import activity, system
from app.utils.websocket_manager import gps_connections


print("Shipment module imported")
print("GPS Tracking module imported")


app = FastAPI(title="FleetFlow API")


@app.on_event("startup")
async def start_realtime_services():
    validate_production_security()
    await gps_connections.start()


@app.on_event("shutdown")
async def stop_realtime_services():
    await gps_connections.stop()

# =========================
# CORS CONFIGURATION
# =========================

allowed_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()]
if not allowed_origins and os.getenv("ENVIRONMENT", "development").lower() != "production":
    allowed_origins = [
        "http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "http://localhost:5176", "http://localhost:5177", "http://localhost:5178",
        "http://127.0.0.1:5173", "http://127.0.0.1:5174", "http://127.0.0.1:5175", "http://127.0.0.1:5176", "http://127.0.0.1:5177", "http://127.0.0.1:5178",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# AUTHENTICATION
# =========================

app.include_router(
    auth.router,
    prefix="/api/auth",
    tags=["Authentication"],
)


# =========================
# SHIPMENT
# =========================

app.include_router(
    shipment.router,
    prefix="/api",
)


# =========================
# GPS TRACKING
# =========================

app.include_router(
    gps_tracking.router,
    prefix="/api",
)


# =========================
# VEHICLES
# =========================

app.include_router(
    vehicle.router,
    prefix="/api",
)


# =========================
# TRIPS
# =========================

app.include_router(
    trip.router,
    prefix="/api",
)


# =========================
# DRIVERS
# =========================

app.include_router(
    driver.router,
    prefix="/api",
)


# =========================
# MAINTENANCE
# =========================

app.include_router(
    maintenance.router,
    prefix="/api",
)


# =========================
# FUEL RECORDS
# =========================

app.include_router(
    fuel_record.router,
    prefix="/api",
)


# =========================
# NOTIFICATIONS
# =========================

app.include_router(
    notification.router,
    prefix="/api",
)


# =========================
# ATTENDANCE
# =========================

app.include_router(
    attendance.router,
    prefix="/api",
)


# =========================
# DASHBOARD
# =========================

app.include_router(
    dashboard.router,
    prefix="/api",
)


# =========================
# REPORTS
# =========================

app.include_router(
    reports.router,
    prefix="/api",
)

app.include_router(leave_request.router, prefix="/api")
app.include_router(activity.router, prefix="/api")
app.include_router(system.router, prefix="/api")


# =========================
# ROOT
# =========================

@app.get("/api/health")
def health_check():
    return {
        "message": "FleetFlow API running"
    }


# A production build of the React application is served by this same FastAPI
# process.  API routes are registered above under /api, so the catch-all route
# below safely supports React Router URLs such as /dashboard and /reports.
frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
assets_dir = frontend_dist / "assets"

if assets_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")


@app.get("/{full_path:path}", include_in_schema=False)
def serve_frontend(full_path: str):
    requested_file = frontend_dist / full_path
    if requested_file.is_file():
        return FileResponse(requested_file)

    index_file = frontend_dist / "index.html"
    if index_file.is_file():
        return FileResponse(index_file)

    return {
        "message": "Frontend build not found. Run the project launcher from the project root."
    }
