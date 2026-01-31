from firecrawl import FirecrawlApp
from pydantic import BaseModel, Field
from typing import List, Optional, Enum
from src.config import config
import resend

app = FirecrawlApp(api_key="fc-29a5fd3db63d4b1fb909b232de75a074")
app_resend = resend(api_key="re_MPbsi958_26tHbygWsVLXT6W9rMmdDqkD")

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

class NGOType(str, Enum):
    LOCAL = "local"
    NATIONAL = "national"  
    INTERNATIONAL = "international"

class NGO(BaseModel):
    name: str = Field(description="Official name of the NGO")
    contact_email: str = Field(description="Primary contact email address")
    phone: str = Field(default="", description="Contact phone number if available")
    website: str = Field(description="NGO website URL")
    ngo_type: NGOType = Field(description="Whether NGO is local, national, or international")
    aid_type: str = Field(description="Primary aid type: medical, food/water, shelter, search & rescue, or general relief")

class NGOList(BaseModel):
    ngos: List[NGO] = Field(description="List of NGOs")

# run a function which "takes in" a list of url news sources and returns a list of disasters
def find_disasters() -> DisasterList:
    print("Finding disasters...")
    return app.agent(
        prompt='''
        Search news sources for the 5 most significant global disasters that occurred in the LAST 24 HOURS ONLY.
        CRITICAL: Only include disasters that started or significantly escalated within the past 24 hours. 
        Reject any disaster older than 24 hours, even if still ongoing.
        Return exactly 5 disasters, prioritized by severity and humanitarian impact.
        Include: earthquakes, floods, fires, storms, landslides, industrial accidents.
        Only disasters where NGOs could provide aid (populated areas, significant casualties or displacement)
        ''',
        schema=DisasterList,
        model="spark-1-pro"
    )

# for each disaster different function finds relevant NGOs
def find_ngos(disaster: Disaster) -> NGOList:
    print(f"Finding NGOs for disaster: {disaster.title}")
    return app.agent(
        prompt=f'''
        Find 5 MAXIMUM distinct NGOs that could assist with this disaster: {disaster}

        CRITICAL: You MUST find a real contact email for each NGO. Visit their website's contact page to find it.
        - Only include NGOs where you can find an actual contact email address
        - Skip any NGO if you cannot locate their email
        - NO DUPLICATES
        ''',
        schema=NGOList,
        model="spark-1-pro"
    )

# for each NGO, email is sent with disaster information
def send_email(ngo: NGO, disaster: Disaster):
    print(f"Sending email to {ngo.name} for disaster: {disaster.title}")
    def send_email(to_email: str, subject: str, html: str, reply_to: str | None = None):
        params = {
            "from": config.from_email,      # e.g. "Acme <onboarding@resend.dev>"
            "to": [to_email],              # must be a list
            "subject": subject,
            "html": html,
        }
        if reply_to:
            params["reply_to"] = reply_to

        return resend.Emails.send(params)

# 1) extract disasters
disasters = find_disasters()
if not disasters:
    print("No disasters found")
    exit()

for disaster in disasters:
    ngos = find_ngos(disaster)
    send_email(ngos, disaster)