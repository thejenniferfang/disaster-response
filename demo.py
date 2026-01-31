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
    location: str = Field(description="Location of the disaster")
    country: str = Field(description="Country of the disaster")
    region: str = Field(description="Region of the disaster")
    latitude: float = Field(description="Latitude coordinate")
    longitude: float = Field(description="Longitude coordinate")
    source_url: str = Field(description="Source URL of the disaster")
    source_name: str = Field(description="Source Name of the disaster")


class ExtractedDisaster(BaseModel):
    disasters: list[Disaster] = Field(description="List of disasters") # list of disasters extracted from the urls
    urls: list[str] = Field(description="List of urls") # list of urls from which the disasters were extracted

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


class NGOType(str, Enum):
    """High-level NGO category (small fixed set, good for validation)."""

    LOCAL = "local"
    NATIONAL = "national"
    INTERNATIONAL = "international"
    GOVERNMENT_PARTNER = "government_partner"
    OTHER = "other"


class VerificationStatus(str, Enum):
    """Verification state for credibility / filtering."""

    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    FLAGGED = "flagged"

class NGO(BaseModel):
    """An NGO that can respond to disasters."""
    
    id: Optional[str] = Field(default=None, description="MongoDB ObjectId as string")
    
    # Core info
    name: str
    description: Optional[str] = None
    ngo_type: NGOType = NGOType.OTHER
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    
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


class NGOList(BaseModel):
    ngos: List[NGO] = Field(description="List of NGOs")

# run a function which "takes in" a list of url news sources and returns a list of disasters
def find_disasters():
    result = app.agent(
        prompt='''
        Search the web for global disasters or serious incidents that NGOs could provide assistance to occuring within the last 24 hours. 
        For each real world disaster, only return one list entry (NO DUPLICATES). 
        Ensure it is within the last 24 hours and of a scale/in a location that NGOs could provide assistance to.
        For example, a hurricane that occurred 2 days ago in the ocean is not a real world disaster.
        ''',
        schema=Disaster,
        model="spark-1-pro"
    )

# for each disaster different function finds relevant NGOs
def find_ngos(disaster: Disaster):
    print(f"Finding NGOs for disaster: {disaster.title}")
    result = app.agent(
        prompt=f'''
        Search the web for NGOs could provide assistance to the following disaster: {disaster.model_dump_json()}
        For each NGO, only return one list entry (NO DUPLICATES). 
        Return at least 5 distinct relevant NGOs if they exist.
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