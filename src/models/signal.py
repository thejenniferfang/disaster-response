"""Signal model - small extracted facts derived from raw pages."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Signal(BaseModel):
    """One extracted, queryable fact (core abstraction)."""

    id: Optional[str] = Field(default=None, description="MongoDB ObjectId as string")

    raw_page_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    region: str
    signal_type: str  # e.g. "infrastructure_outage", "earthquake", "evacuation"
    keywords: list[str] = Field(default_factory=list)

    source_confidence: float = 0.5

    # Optional provenance about how region was derived (judge-friendly)
    region_source: Optional[str] = None  # "heuristic" | "ner" | "llm"
    region_confidence: Optional[float] = None

