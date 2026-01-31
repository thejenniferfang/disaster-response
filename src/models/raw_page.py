"""RawPage model - one Firecrawl fetch stored verbatim-ish."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class RawPage(BaseModel):
    """A single fetched page/document (ground truth)."""

    id: Optional[str] = Field(default=None, description="MongoDB ObjectId as string")

    url: str
    fetched_at: datetime = Field(default_factory=datetime.utcnow)

    # Optional lightweight classification metadata (not heavy processing)
    source_type: Optional[str] = None  # e.g. "government", "news", "ngo"
    region: Optional[str] = None  # coarse region/country hint (optional)

    # Raw content
    content: str  # full text/markdown
    content_hash: str

    # Any Firecrawl metadata (title, siteName, etc.)
    metadata: dict[str, Any] = Field(default_factory=dict)

