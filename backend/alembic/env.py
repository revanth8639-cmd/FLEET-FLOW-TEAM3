from logging.config import fileConfig
import os

from sqlalchemy import engine_from_config, pool
from alembic import context

from app.database import Base, DATABASE_URL

# Import all models so Alembic can detect tables
from app.models import (
    user,
    driver,
    vehicle,
    shipment,
    trip,
    gps_tracking,
    maintenance,
    fuel_record,
    notification,
    attendance,
    activity_log,
)

# Alembic Config object
config = context.config
if DATABASE_URL:
    # Reuse the same host/Docker normalization as the application engine.
    # This keeps local Windows migrations from trying to resolve the Docker
    # hostname ``host.docker.internal``.
    config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Configure Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# SQLAlchemy metadata for autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in offline mode."""

    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in online mode."""

    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
