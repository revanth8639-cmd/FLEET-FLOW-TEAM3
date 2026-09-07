from uuid import UUID

from sqlalchemy.orm import Session

from app.models.activity_log import ActivityLog


def record_activity(
    db: Session,
    user_id: UUID | None,
    action: str,
    entity_type: str | None = None,
    entity_id: UUID | str | None = None,
) -> None:
    """Queue an operational audit event in the current transaction."""
    db.add(
        ActivityLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
        )
    )
