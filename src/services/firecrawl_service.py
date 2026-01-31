"""
Firecrawl Service - monitors web for disasters and incidents.

TEAM MEMBER 1: This is your primary file to work on.
Responsible for: Web scraping, disaster detection, parsing disaster info.
"""

from typing import Optional
from firecrawl import FirecrawlApp

from src.config import config
from src.models import Disaster, DisasterType, DisasterSeverity
from src.database import DisasterRepository


class FirecrawlService:
    """Service for monitoring web sources for disasters using Firecrawl."""
    
    def __init__(self):
        self._app = FirecrawlApp(api_key=config.firecrawl_api_key)
        self._disaster_repo = DisasterRepository()
    
    def scrape_url(self, url: str) -> Optional[dict]:
        """
        Scrape a single URL for content.
        
        Returns the scraped content or None if failed.
        """
        try:
            result = self._app.scrape_url(url, params={"formats": ["markdown"]})
            return result
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return None
    
    def search_for_disasters(self, query: str) -> list[dict]:
        """
        Search the web for disaster-related content.
        
        Args:
            query: Search query (e.g., "earthquake California 2024")
        
        Returns:
            List of search results with content.
        """
        # TODO: Implement using Firecrawl's search/crawl capabilities
        # This is a placeholder - expand based on Firecrawl API
        try:
            # Example: Use crawl or search endpoint
            results = self._app.search(query)
            return results if results else []
        except Exception as e:
            print(f"Error searching for '{query}': {e}")
            return []
    
    def parse_disaster_from_content(self, content: dict, source_url: str) -> Optional[Disaster]:
        """
        Parse scraped content into a Disaster object.
        
        TODO: Implement parsing logic - could use:
        - Keyword matching
        - LLM extraction
        - Pattern recognition
        
        Args:
            content: Scraped content from Firecrawl
            source_url: The URL that was scraped
        
        Returns:
            Disaster object if content contains disaster info, None otherwise.
        """
        # Placeholder implementation - team member should expand this
        markdown = content.get("markdown", "")
        
        if not markdown:
            return None
        
        # Basic keyword detection (expand this!)
        disaster_type = self._detect_disaster_type(markdown)
        if disaster_type is None:
            return None
        
        # Extract other fields (expand this!)
        title = content.get("metadata", {}).get("title", "Unknown Disaster")
        
        return Disaster(
            disaster_type=disaster_type,
            severity=DisasterSeverity.MEDIUM,  # TODO: Detect severity
            title=title,
            description=markdown[:500],  # Truncate for now
            location="Unknown",  # TODO: Extract location
            source_url=source_url,
            source_name=content.get("metadata", {}).get("siteName"),
        )
    
    def _detect_disaster_type(self, text: str) -> Optional[DisasterType]:
        """Detect disaster type from text content."""
        text_lower = text.lower()
        
        type_keywords = {
            DisasterType.EARTHQUAKE: ["earthquake", "seismic", "tremor", "quake"],
            DisasterType.FLOOD: ["flood", "flooding", "inundation"],
            DisasterType.FIRE: ["wildfire", "forest fire", "bushfire", "fire outbreak"],
            DisasterType.HURRICANE: ["hurricane", "cyclone", "typhoon"],
            DisasterType.TORNADO: ["tornado", "twister"],
            DisasterType.TSUNAMI: ["tsunami", "tidal wave"],
            DisasterType.LANDSLIDE: ["landslide", "mudslide"],
            DisasterType.DROUGHT: ["drought", "water shortage"],
            DisasterType.PANDEMIC: ["pandemic", "epidemic", "outbreak", "disease spread"],
            DisasterType.INDUSTRIAL_ACCIDENT: ["industrial accident", "chemical spill", "explosion"],
        }
        
        for disaster_type, keywords in type_keywords.items():
            if any(kw in text_lower for kw in keywords):
                return disaster_type
        
        return None
    
    def monitor_sources(self, urls: list[str]) -> list[Disaster]:
        """
        Monitor a list of URLs for disasters.
        
        Args:
            urls: List of news/monitoring URLs to check
        
        Returns:
            List of detected disasters (already saved to DB).
        """
        detected = []
        
        for url in urls:
            content = self.scrape_url(url)
            if content:
                disaster = self.parse_disaster_from_content(content, url)
                if disaster:
                    # Save to database
                    disaster_id = self._disaster_repo.insert(disaster)
                    disaster.id = disaster_id
                    detected.append(disaster)
                    print(f"Detected disaster: {disaster.title}")
        
        return detected
