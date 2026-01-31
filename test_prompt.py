from firecrawl import FirecrawlApp
from pydantic import BaseModel, Field
from typing import List
from enum import Enum

app = FirecrawlApp(api_key="fc-29a5fd3db63d4b1fb909b232de75a074")

class DisasterType(str, Enum):
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
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Disaster(BaseModel):
    name: str = Field(description="Name of the disaster")
    disaster_type: DisasterType = Field(description="Disaster Type")
    severity: DisasterSeverity = Field(description="Severity of the disaster")
    location: str = Field(description="Location of the disaster")
    country: str = Field(description="Country of the disaster")
    region: str = Field(description="Region of the disaster")
    latitude: float = Field(description="Latitude coordinate")
    longitude: float = Field(description="Longitude coordinate")
    source_url: str = Field(description="Source URL of the disaster")
    source_name: str = Field(description="Source Name of the disaster")

# === PROMPT TO ITERATE ON ===
PROMPT = '''
Search multiple news sources (Reuters, BBC, Al Jazeera, AP News, local news) to find ALL global disasters from the last 24 hours.

Return EACH disaster separately. Find at least 5 distinct disasters if they exist.

Include: earthquakes, floods, fires, storms, industrial accidents, etc.
Only include disasters where NGOs could realistically provide aid (populated areas, significant impact).
'''

if __name__ == "__main__":
    result = app.agent(prompt=PROMPT, schema=Disaster, model="spark-1-pro")
    print("\n=== RESULT ===")
    print(result)
