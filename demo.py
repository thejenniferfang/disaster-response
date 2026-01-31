from firecrawl import FirecrawlApp
from pydantic import BaseModel, Field
from typing import List, Optional, Enum

app = FirecrawlApp(api_key="fc-29a5fd3db63d4b1fb909b232de75a074")

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
    name: str = Field(description="Name of the disaster")
    disaster_type: DisasterType = Field(description="Disaster Type")
    severity: DisasterSeverity = Field(description="Severity of the disaster")
    location: str = Field(description="Location of the disaster")
    country: str = Field(description="Country of the disaster")
    region: str = Field(description="Region of the disaster")
    coordinates: tuple[float, float] = Field(description="Coordinates of the disaster")
    source_url: str = Field(description="Source URL of the disaster")
    source_name: str = Field(description="Source Name of the disaster")


class ExtractedDisaster(BaseModel):
    disasters: list[Disaster] = Field(description="List of disasters") # list of disasters extracted from the urls
    urls: list[str] = Field(description="List of urls") # list of urls from which the disasters were extracted


class NGO:
    def __init__(self, name: str):
        self.name = name

# run a function which "takes in" a list of url news sources and returns a list of disasters
def find_disasters(urls: list[str]):
    for url in urls:
        pass

# for each disaster different function finds relevant NGOs
def find_ngos(disaster: Disaster):
    print(f"Finding NGOs for disaster: {disaster.title}")

# for each NGO, email is sent with disaster information
def send_email(ngo: NGO, disaster: Disaster):
    print(f"Sending email to {ngo.name} for disaster: {disaster.title}")

result = app.agent(
    prompt="Extract the disasters from the following urls: {urls}",
    schema=ExtractedDisaster,
    urls=["https://www.google.com", "https://www.yahoo.com", "https://www.bing.com", "newyorktimes.com", "sfchronicle.com"]
)