"""Disaster model - represents a detected disaster or incident."""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class DisasterType(str, Enum):
    """Types of disasters the system can detect."""
    EARTHQUAKE = "earthquake"
    FLOOD = "flood"
    FIRE = "fire"
    HURRICANE = "hurricane"
    TORNADO = "tornado"
    TSUNAMI = "tsunami"
    LANDSLIDE = "landslide"
    DROUGHT = "drought"
    PANDEMIC = "pandemic"
    INDUSTRIAL_ACCIDENT = "industrial_accident"
    OTHER = "other"


class DisasterSeverity(str, Enum):
    """Severity levels for disasters."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Disaster(BaseModel):
    """A detected disaster or incident."""
    
    id: Optional[str] = Field(default=None, description="MongoDB ObjectId as string")
    
    # Core info
    disaster_type: DisasterType
    severity: DisasterSeverity
    title: str
    description: str
    
    # Location
    location: str  # Human readable location
    country: Optional[str] = None
    region: Optional[str] = None
    coordinates: Optional[tuple[float, float]] = None  # (lat, lon)
    
    # Source info
    source_url: str
    source_name: Optional[str] = None
    
    # Timestamps
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    occurred_at: Optional[datetime] = None
    
    # Processing status
    processed: bool = False
    ngos_notified: list[str] = Field(default_factory=list)  # List of NGO IDs
    
    class Config:
        use_enum_values = True
