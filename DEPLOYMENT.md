# FleetFlow deployment

FleetFlow runs as a single Docker Compose stack: FastAPI serves the compiled React app, PostgreSQL stores data, and Redis/Celery handle scheduled checks.

1. Copy `.env.example` to `.env` and set a long, unique `POSTGRES_PASSWORD`.
2. Copy `backend/.env.example` to `backend/.env`. Set a unique `SECRET_KEY` of at least 32 characters. Configure `MAIL_*`, Twilio, and Maps values only when those integrations are required. For a separate frontend origin, set `CORS_ORIGINS` to its HTTPS URL.
3. Build and start: `docker compose up --build -d`.
4. Confirm `http://YOUR_HOST:8000/api/health` responds, then inspect `docker compose logs backend celery_worker celery_beat`.

Do not publish PostgreSQL or Redis ports in production. Back up the named `fleetflow_postgres` volume before upgrades. Use HTTPS and a reverse proxy/load balancer in front of port 8000; set the public hostname and TLS there.

Before a public launch, rotate any credentials that have previously appeared in local files, terminals, screenshots, or commits.
