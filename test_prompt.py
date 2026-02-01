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
    occurred_at: str = Field(description="Date/time when the disaster occurred, ISO 8601 format")
    location: str = Field(description="Location of the disaster")
    country: str = Field(description="Country of the disaster")
    region: str = Field(description="Region of the disaster")
    latitude: float = Field(description="Latitude coordinate")
    longitude: float = Field(description="Longitude coordinate")
    source_url: str = Field(description="Source URL of the disaster")
    source_name: str = Field(description="Source Name of the disaster")

class DisasterList(BaseModel):
    disasters: List[Disaster] = Field(description="List of all disasters found")

# === PROMPT TO ITERATE ON ===
PROMPT = '''
Search news sources for the 5 most significant global disasters that occurred in the LAST 24 HOURS ONLY.

CRITICAL: Only include disasters that started or significantly escalated within the past 24 hours. 
Reject any disaster older than 24 hours, even if still ongoing.

Return exactly 5 disasters, prioritized by severity and humanitarian impact.

Include: earthquakes, floods, fires, storms, landslides, industrial accidents.
Only disasters where NGOs could provide aid (populated areas, significant casualties or displacement).
'''

if __name__ == "__main__":
    result = app.agent(prompt=PROMPT, schema=DisasterList, model="spark-1-pro")
    print("\n=== RESULT ===")
    if result.success and result.data:
        for d in result.data.get("disasters", []):
            print(f"\n- {d['name']} ({d['disaster_type']})")
            print(f"  {d['location']}, {d['country']} | {d.get('occurred_at', 'N/A')}")
    else:
        print(result)
