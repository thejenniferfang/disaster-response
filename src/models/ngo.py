"""NGO model - represents an NGO that can respond to disasters."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class NGOCapability(str, Enum):
    """Capabilities/specializations of NGOs."""
    SEARCH_AND_RESCUE = "search_and_rescue"
    MEDICAL_AID = "medical_aid"
    FOOD_AND_WATER = "food_and_water"
    SHELTER = "shelter"
    EVACUATION = "evacuation"
    REBUILDING = "rebuilding"
    PSYCHOLOGICAL_SUPPORT = "psychological_support"
    LOGISTICS = "logistics"
    COMMUNICATIONS = "communications"
    GENERAL_RELIEF = "general_relief"


class NGO(BaseModel):
    """An NGO that can respond to disasters."""
    
    id: Optional[str] = Field(default=None, description="MongoDB ObjectId as string")
    
    # Core info
    name: str
    description: Optional[str] = None
    
    # Contact
    email: str  # Primary contact email
    contact_name: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    
    # Capabilities and coverage
    capabilities: list[NGOCapability] = Field(default_factory=list)
    disaster_types: list[str] = Field(default_factory=list)  # DisasterType values they handle
    
    # Geographic coverage
    countries: list[str] = Field(default_factory=list)  # Countries they operate in
    regions: list[str] = Field(default_factory=list)  # Specific regions
    is_global: bool = False  # Operates worldwide
    
    # Status
    active: bool = True
    
    class Config:
        use_enum_values = True
