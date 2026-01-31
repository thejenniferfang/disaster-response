"""
Extraction Schemas - Pydantic models defining what to extract from pages.

These schemas are used with Firecrawl's LLM extraction.
The LLM reads any page and extracts data matching these structures.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ExtractedDisasterInfo(BaseModel):
    """
    Schema for extracting disaster/incident information from any page.
    
    The LLM will attempt to find and extract this information
    regardless of the page's layout or structure.
    """
    
    # What happened
    disaster_type: str = Field(
        description="Type of disaster: earthquake, flood, fire, hurricane, tornado, tsunami, landslide, drought, pandemic, industrial_accident, or other"
    )
    title: str = Field(
        description="Brief title or headline describing the incident"
    )
    description: str = Field(
        description="Detailed description of what happened"
    )
    
    # Severity assessment
    severity: str = Field(
        description="Severity level: low, medium, high, or critical"
    )
    
    # Location
    location: str = Field(
        description="Human-readable location where the disaster occurred"
    )
    country: Optional[str] = Field(
        default=None,
        description="Country where the disaster occurred"
    )
    region: Optional[str] = Field(
        default=None,
        description="State, province, or region"
    )
    
    # Timing
    occurred_at: Optional[str] = Field(
        default=None,
        description="When the disaster occurred (ISO format if possible)"
    )
    
    # Impact
    casualties: Optional[int] = Field(
        default=None,
        description="Number of casualties if mentioned"
    )
    affected_population: Optional[int] = Field(
        default=None,
        description="Number of people affected if mentioned"
    )
    
    # Confidence
    is_confirmed_disaster: bool = Field(
        description="True if this page clearly describes an actual disaster/emergency, False if uncertain or unrelated"
    )


class ExtractedDisasterList(BaseModel):
    """
    Schema for pages that list multiple disasters (e.g., news aggregators).
    """
    
    disasters: list[ExtractedDisasterInfo] = Field(
        default_factory=list,
        description="List of disasters found on this page"
    )


# Prompts to guide extraction
SINGLE_DISASTER_PROMPT = """
Extract information about any natural disaster, emergency, or crisis mentioned on this page.
Focus on: earthquakes, floods, fires, hurricanes, tornadoes, tsunamis, landslides, 
droughts, pandemics, and industrial accidents.

Only extract if there is a clear disaster or emergency being reported.
Set is_confirmed_disaster to False if the content is not about an actual disaster.
"""

MULTIPLE_DISASTERS_PROMPT = """
This page may contain information about multiple disasters or emergencies.
Extract all distinct disasters mentioned, including natural disasters, 
emergencies, and crises.

For each disaster, capture: type, location, severity, and description.
Only include confirmed disasters, not predictions or historical references.
"""
