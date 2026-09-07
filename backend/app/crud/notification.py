from datetime import datetime

from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.schemas.notification import (
    NotificationCreate,
    NotificationUpdate,
)


def create_notification(db: Session, notification: NotificationCreate):
    db_notification = Notification(
        **notification.model_dump()
    )

    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)

    return db_notification


def get_notifications(db: Session):
    return db.query(Notification).order_by(Notification.created_at.desc()).all()


def mark_notification_read(db: Session, notification_id):
    notification = get_notification(db, notification_id)
    if not notification:
        return None
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification


def mark_all_notifications_read(db: Session, user_id):
    count = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read.is_(False),
    ).update({"is_read": True}, synchronize_session=False)
    db.commit()
    return count


def add_notification(db: Session, user_id, title: str, message: str, notification_type: str = "info"):
    """Create an event notification without requiring a request schema."""
    item = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=notification_type,
        created_at=datetime.utcnow(),
    )
    db.add(item)
    return item


def add_notifications(db: Session, user_ids, title: str, message: str, notification_type: str = "info"):
    for user_id in set(user_ids):
        if user_id:
            add_notification(db, user_id, title, message, notification_type)


def get_notification(db: Session, notification_id):
    return db.query(Notification).filter(
        Notification.notification_id == notification_id
    ).first()


def update_notification(
    db: Session,
    notification_id,
    notification: NotificationUpdate
):
    db_notification = get_notification(db, notification_id)

    if not db_notification:
        return None

    for key, value in notification.model_dump(exclude_unset=True).items():
        setattr(db_notification, key, value)

    db.commit()
    db.refresh(db_notification)

    return db_notification


def delete_notification(db: Session, notification_id):
    db_notification = get_notification(db, notification_id)

    if not db_notification:
        return None

    db.delete(db_notification)
    db.commit()

    return db_notification
