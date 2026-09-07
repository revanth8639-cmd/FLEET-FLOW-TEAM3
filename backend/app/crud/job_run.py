from datetime import datetime

from app.models.job_run import JobRun


def start_job(db, task_name: str) -> JobRun:
    run = JobRun(task_name=task_name, started_at=datetime.utcnow())
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def finish_job(db, run: JobRun, *, success: bool, result: str | None = None, error: str | None = None) -> None:
    run.finished_at = datetime.utcnow()
    run.success = success
    run.result = result
    run.error = error
    db.commit()
