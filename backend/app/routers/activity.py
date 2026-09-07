from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.database import get_db
from app.models.activity_log import ActivityLog
from app.schemas.activity_log import ActivityLogOut

router = APIRouter(prefix="/activity", tags=["System Activity"])


@router.get("/", response_model=list[ActivityLogOut])
def read_activity_logs(limit: int = 50, db: Session = Depends(get_db), current_user=Depends(require_roles("Admin"))):
    return db.query(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(max(1, min(limit, 200))).all()
