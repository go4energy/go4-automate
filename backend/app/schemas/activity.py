"""Activity log schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ActivityLogResponse(BaseModel):
    """Activity log entry response."""

    id: int
    module: str
    action: str
    title: str
    detail: str | None = None
    entity_type: str | None = None
    entity_id: int | None = None
    severity: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActivityStatsResponse(BaseModel):
    """Aggregated activity stats per module."""

    module: str
    total: int
    actions: dict[str, int]
