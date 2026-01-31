"""Event model - aggregated incident derived from multiple signals."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Event(BaseModel):
    """An emerging/active crisis event users care about."""

    id: Optional[str] = Field(default=None, description="MongoDB ObjectId as string")

    event_type: str  # typically derived from signal_type
    region: str

    first_detected: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    confidence_score: float = 0.0
    supporting_signals: list[str] = Field(default_factory=list)  # ObjectId strings

    status: str = "active"  # "active" | "resolved" | "dismissed"

