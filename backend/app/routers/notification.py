from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_current_user
from app.models.notification import Notification

from app.schemas.notification import (
    NotificationOut,
)

from app.crud.notification import (
    get_notifications,
    get_notification,
    mark_notification_read,
    mark_all_notifications_read,
)

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"]
)


@router.get("/", response_model=list[NotificationOut])
def read_notifications(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Notifications are system events addressed to one user. Every role,
    # including Admin, is limited to its own inbox.
    return [item for item in get_notifications(db) if item.user_id == current_user.user_id]


@router.post("/read-all")
def mark_all_read(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    count = mark_all_notifications_read(db, current_user.user_id)
    return {"message": "Notifications marked as read", "updated": count}


@router.get("/{notification_id}", response_model=NotificationOut)
def read_notification(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    notification = get_notification(
        db,
        notification_id
    )

    if not notification:
        raise HTTPException(
            status_code=404,
            detail="Notification not found"
        )

    if notification.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="You do not have access to this notification")
    return notification


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_read(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    existing = get_notification(db, notification_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Notification not found")
    if existing.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="You can update only your own notifications")
    return mark_notification_read(db, notification_id)
