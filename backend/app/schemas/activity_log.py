from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ActivityLogOut(BaseModel):
    activity_id: UUID
    user_id: UUID | None
    action: str
    entity_type: str | None
    entity_id: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
