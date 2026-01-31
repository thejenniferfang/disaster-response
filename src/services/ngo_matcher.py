"""
NGO Matcher Service - finds relevant NGOs for disasters.

TEAM MEMBER 2: This is your primary file to work on.
Responsible for: NGO matching logic, relevance scoring, filtering.
"""

from typing import Optional

from src.models import Disaster, NGO, DisasterType, NGOCapability
from src.database import NGORepository


# Mapping of disaster types to relevant NGO capabilities
DISASTER_CAPABILITY_MAP: dict[DisasterType, list[NGOCapability]] = {
    DisasterType.EARTHQUAKE: [
        NGOCapability.SEARCH_AND_RESCUE,
        NGOCapability.MEDICAL_AID,
        NGOCapability.SHELTER,
        NGOCapability.REBUILDING,
    ],
    DisasterType.FLOOD: [
        NGOCapability.EVACUATION,
        NGOCapability.SHELTER,
        NGOCapability.FOOD_AND_WATER,
        NGOCapability.MEDICAL_AID,
    ],
    DisasterType.FIRE: [
        NGOCapability.EVACUATION,
        NGOCapability.SHELTER,
        NGOCapability.MEDICAL_AID,
    ],
    DisasterType.HURRICANE: [
        NGOCapability.EVACUATION,
        NGOCapability.SHELTER,
        NGOCapability.FOOD_AND_WATER,
        NGOCapability.REBUILDING,
    ],
    DisasterType.TORNADO: [
        NGOCapability.SEARCH_AND_RESCUE,
        NGOCapability.SHELTER,
        NGOCapability.MEDICAL_AID,
    ],
    DisasterType.TSUNAMI: [
        NGOCapability.SEARCH_AND_RESCUE,
        NGOCapability.EVACUATION,
        NGOCapability.MEDICAL_AID,
        NGOCapability.SHELTER,
    ],
    DisasterType.PANDEMIC: [
        NGOCapability.MEDICAL_AID,
        NGOCapability.LOGISTICS,
        NGOCapability.COMMUNICATIONS,
    ],
    # Add more mappings as needed
}


class NGOMatcher:
    """Service for matching NGOs to disasters based on relevance."""
    
    def __init__(self):
        self._ngo_repo = NGORepository()
    
    def find_relevant_ngos(self, disaster: Disaster) -> list[NGO]:
        """
        Find NGOs relevant to a disaster.
        
        Matching criteria:
        1. Geographic match (country/region or global)
        2. Disaster type match
        3. Capability match
        
        Args:
            disaster: The disaster to find NGOs for
        
        Returns:
            List of relevant NGOs, sorted by relevance score.
        """
        all_ngos = self._ngo_repo.find_all_active()
        
        scored_ngos: list[tuple[NGO, float]] = []
        
        for ngo in all_ngos:
            score = self._calculate_relevance_score(ngo, disaster)
            if score > 0:
                scored_ngos.append((ngo, score))
        
        # Sort by score descending
        scored_ngos.sort(key=lambda x: x[1], reverse=True)
        
        return [ngo for ngo, _ in scored_ngos]
    
    def _calculate_relevance_score(self, ngo: NGO, disaster: Disaster) -> float:
        """
        Calculate relevance score for an NGO given a disaster.
        
        Returns a score from 0 to 1, where 0 means not relevant.
        """
        score = 0.0
        
        # Geographic match (required - returns 0 if no match)
        geo_score = self._geographic_match_score(ngo, disaster)
        if geo_score == 0:
            return 0.0
        score += geo_score * 0.4  # 40% weight
        
        # Disaster type match
        type_score = self._disaster_type_match_score(ngo, disaster)
        score += type_score * 0.3  # 30% weight
        
        # Capability match
        capability_score = self._capability_match_score(ngo, disaster)
        score += capability_score * 0.3  # 30% weight
        
        return score
    
    def _geographic_match_score(self, ngo: NGO, disaster: Disaster) -> float:
        """Calculate geographic match score."""
        # Global NGOs always match
        if ngo.is_global:
            return 0.7  # Slightly lower score than local match
        
        # Check country match
        if disaster.country and disaster.country in ngo.countries:
            # Check region match for bonus
            if disaster.region and disaster.region in ngo.regions:
                return 1.0  # Perfect match
            return 0.9  # Country match
        
        # No geographic match
        return 0.0
    
    def _disaster_type_match_score(self, ngo: NGO, disaster: Disaster) -> float:
        """Calculate disaster type match score."""
        if not ngo.disaster_types:
            # NGO handles all types (general relief)
            return 0.5
        
        disaster_type_value = disaster.disaster_type
        if isinstance(disaster.disaster_type, DisasterType):
            disaster_type_value = disaster.disaster_type.value
            
        if disaster_type_value in ngo.disaster_types:
            return 1.0
        
        return 0.0
    
    def _capability_match_score(self, ngo: NGO, disaster: Disaster) -> float:
        """Calculate capability match score based on disaster needs."""
        if not ngo.capabilities:
            return 0.3  # Some baseline for general NGOs
        
        # Get needed capabilities for this disaster type
        disaster_type = disaster.disaster_type
        if isinstance(disaster_type, str):
            disaster_type = DisasterType(disaster_type)
            
        needed_capabilities = DISASTER_CAPABILITY_MAP.get(disaster_type, [])
        
        if not needed_capabilities:
            return 0.5  # Unknown disaster type, partial match
        
        # Calculate overlap
        ngo_caps = set(ngo.capabilities)
        needed_caps = set(cap.value if isinstance(cap, NGOCapability) else cap 
                         for cap in needed_capabilities)
        
        # Convert NGO caps to values for comparison
        ngo_cap_values = set(
            cap.value if isinstance(cap, NGOCapability) else cap 
            for cap in ngo_caps
        )
        
        overlap = len(ngo_cap_values & needed_caps)
        if overlap == 0:
            return 0.0
        
        return overlap / len(needed_caps)
    
    def get_top_ngos(self, disaster: Disaster, limit: int = 10) -> list[NGO]:
        """Get top N most relevant NGOs for a disaster."""
        relevant = self.find_relevant_ngos(disaster)
        return relevant[:limit]
