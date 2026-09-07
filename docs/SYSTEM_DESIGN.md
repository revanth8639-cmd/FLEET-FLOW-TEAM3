# FleetFlow system design

```text
React + Leaflet ──HTTP/WebSocket──> FastAPI ──SQLAlchemy/Alembic──> PostgreSQL
                                      │
                                      ├── Redis Pub/Sub (GPS fan-out / route cache)
                                      └── Celery Worker + Beat (maintenance and shipment checks)
```

## Core data flow

`User → Driver → Vehicle → Shipment → Trip → GPS/Fuel/Maintenance`.
All primary and foreign keys are UUIDs. Roles are enforced by FastAPI dependencies: Admin, FleetManager, Dispatcher, and Driver.

## Screen wireframes

```text
Login/Signup: [email] [password] [role] [submit]
Fleet Dashboard: [vehicle totals] [status cards] [maintenance alerts]
Vehicles/Drivers: [filter] [table] [add/edit form]
Shipments/Trips: [status timeline] [assignment] [start/end]
GPS Tracking: [live Leaflet map] [vehicle selector] [location table]
Reports: [fleet/logistics/admin metrics] [fuel and maintenance trends]
```

## Local operations

1. Create `backend/.env` with `DATABASE_URL`, `SECRET_KEY`, and `REDIS_URL`.
2. Run `alembic upgrade head` from `backend`.
3. Run `docker compose up` for Redis, API, Celery worker, and Beat.
4. Run the React dev server separately when not using the built frontend.
