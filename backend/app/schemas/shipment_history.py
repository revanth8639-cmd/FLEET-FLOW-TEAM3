from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class ShipmentHistoryOut(BaseModel):
    history_id: UUID
    shipment_id: UUID
    status: str
    changed_at: datetime
    changed_by_user_id: UUID | None
    model_config = ConfigDict(from_attributes=True)
