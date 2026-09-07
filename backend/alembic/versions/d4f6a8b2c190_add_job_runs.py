"""Persist scheduled Celery job results for system monitoring."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "d4f6a8b2c190"
down_revision = "c2e5f7a1b903"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job_runs",
        sa.Column("run_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("task_name", sa.String(length=150), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=True),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
    )
    op.create_index("ix_job_runs_task_name", "job_runs", ["task_name"])


def downgrade() -> None:
    op.drop_index("ix_job_runs_task_name", table_name="job_runs")
    op.drop_table("job_runs")
