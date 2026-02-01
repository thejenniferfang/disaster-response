from firecrawl import FirecrawlApp
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
from functools import lru_cache
import resend
from typing import Tuple
import hashlib
import time

app = FirecrawlApp(api_key="fc-29a5fd3db63d4b1fb909b232de75a074")
resend.api_key = "re_MPbsi958_26tHbygWsVLXT6W9rMmdDqkD"

SEND_TO_DEMO_EMAIL = True
DEMO_EMAIL = "sgolden26@berkeley.edu"
NUM_DISASTERS = 5
NUM_NGOS = 5

CACHE_FIRECRAWL_DISASTERS = True
CACHE_FIRECRAWL_NGOS = True
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
    if CACHE_FIRECRAWL_DISASTERS:
        import json
        with open('disasterResponseCache.json', 'r') as f:
            cache_data = json.load(f)
        disasters = [Disaster(**disaster_dict) for disaster_dict in cache_data['disasters']]
        time.sleep(3)
        return DisasterList(disasters=disasters)
    else:
        response = app.agent(
            prompt=f'''
            Search news sources for the {NUM_DISASTERS} most significant global disasters that occurred in the LAST 24 HOURS ONLY.
            CRITICAL: Only include disasters that started or significantly escalated within the past 24 hours. 
            Reject any disaster older than 24 hours, even if still ongoing.
            Return exactly {NUM_DISASTERS} disasters, prioritized by severity and humanitarian impact.
            Include: earthquakes, floods, fires, storms, landslides, industrial accidents.
            Only disasters where NGOs could provide aid (populated areas, significant casualties or displacement)
            ''',
            schema=DisasterList,
            model="spark-1-pro"
        )
        return DisasterList(**response.data)

# Mapping of disaster name keywords to NGO cache files
NGO_CACHE_MAP = {
    "rubaya": "rubayaCache.json",
    "mozambique": "mozambiqueCache.json",
    "philippines": "philipinesCache.json",
    "tropical": "tropicalCache.json",
    "storm": "stormCache.json",
}

# for each disaster different function finds relevant NGOs
def find_ngos(disaster: Disaster) -> NGOList:
    print(f"Finding NGOs for disaster: {disaster.name}")
    if CACHE_FIRECRAWL_NGOS:
        import json
        # Find matching cache file based on disaster name
        cache_file = None
        disaster_name_lower = disaster.name.lower()
        for keyword, filename in NGO_CACHE_MAP.items():
            if keyword in disaster_name_lower:
                cache_file = filename
                break
        
        if cache_file:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            ngos = [NGO(**ngo_dict) for ngo_dict in cache_data['ngos']]
            time.sleep(2)
            return NGOList(ngos=ngos)
        else:
            print(f"No cache found for disaster: {disaster.name}")
            time.sleep(2)
            return NGOList(ngos=[])
    else:
        response = app.agent(
            prompt=f'''
            Find {NUM_NGOS} MAXIMUM distinct NGOs that could assist with this disaster: {disaster}

        CRITICAL: You MUST find a real contact email for each NGO. Visit their website's contact page to find it.
        - Only include NGOs where you can find an actual contact email address
        - Skip any NGO if you cannot locate their email
        - NO DUPLICATES
        ''',
        schema=NGOList,
        model="spark-1-pro"
        )
        return NGOList(**response.data)

# for each NGO, email is sent with disaster information
def send_emails(ngoDisasterList: List[Tuple[NGO, Disaster]]):
    params: List[resend.Emails.SendParams] = [
        {
            "from": "onboarding@resend.dev",
            "to": DEMO_EMAIL if SEND_TO_DEMO_EMAIL else ngo.contact_email,
            "subject": f"{"[to " + ngo.contact_email + "] " if SEND_TO_DEMO_EMAIL else ""}Disaster Alert: {disaster.name}",
            "html": f"""
            <html>
            <body>
                <h2>Urgent Disaster Response Alert</h2>
                
                <p>Dear {ngo.name} Team,</p>
                
                <p>We are reaching out to you because your organization has been identified as a potential responder for a recent disaster that requires immediate humanitarian assistance.</p>
                
                <h3>Disaster Information:</h3>
                <ul>
                    <li><strong>Name:</strong> {disaster.name}</li>
                    <li><strong>Type:</strong> {disaster.disaster_type.value}</li>
                    <li><strong>Severity:</strong> {disaster.severity.value}</li>
                    <li><strong>Location:</strong> {disaster.location}, {disaster.country}</li>
                    <li><strong>Region:</strong> {disaster.region}</li>
                    <li><strong>Occurred:</strong> {disaster.occurred_at}</li>
                    <li><strong>Coordinates:</strong> {disaster.latitude}, {disaster.longitude}</li>
                    <li><strong>Source:</strong> <a href="{disaster.source_url}">{disaster.source_name}</a></li>
                </ul>
                
                <p>Your organization's expertise in <strong>{ngo.aid_type}</strong> could be crucial in providing relief to those affected by this disaster.</p>
                
                <p>If your organization is able to respond or coordinate relief efforts, please consider taking action as soon as possible. Time is critical in disaster response situations.</p>
                
                <p>For more information about this disaster, please visit the source link above or contact local emergency management authorities.</p>
                
                <p>Thank you for your continued commitment to humanitarian aid and disaster relief.</p>
                
                <p>Best regards,<br>
                Disaster Response Notification System</p>
                
                <hr>
                <p><small>This is an automated alert system designed to connect NGOs with disaster response opportunities. If you believe you received this message in error, please contact us.</small></p>
            </body>
            </html>
            """,
        } for ngo, disaster in ngoDisasterList
    ]
    print(params)
    return resend.Batch.send(params)

def run_pipeline():
    """Run the full disaster response pipeline."""
    # 1) extract disasters
    disasterlist: DisasterList = find_disasters()
    ngoDisasterList: List[Tuple[NGO, Disaster]] = []
    for disaster in disasterlist.disasters:
        ngos = find_ngos(disaster)
        ngoDisasterList.extend([(ngo, disaster) for ngo in ngos.ngos])
    print(f"Sending emails")
    print(ngoDisasterList)
    print(send_emails(ngoDisasterList))
    return disasterlist, ngoDisasterList

if __name__ == "__main__":
    run_pipeline()
    # params = {
    #         "from": "onboarding@resend.dev",
    #         "to": DEMO_EMAIL,
    #         "subject": f"{"[to " + "] " if SEND_TO_DEMO_EMAIL else ""}Disaster Alert: ",
    #         "html": f"""
    #         <html>
    #         <body>
    #             <h2>Urgent Disaster Response Alert</h2>
                
    #             <p>Dear  Team,</p>
                
    #             <p>We are reaching out to you because your organization has been identified as a potential responder for a recent disaster that requires immediate humanitarian assistance.</p>
                
    #             <h3>Disaster Information:</h3>
    #             <ul>
    #               ng relief to those affected by this disas
                
    #             <p>If your organization is able to respond or coordinate relief efforts, please consider taking action as soon as possible. Time is critical in disaster response situations.</p>
                
    #             <p>For more information about this disaster, please visit the source link above or contact local emergency management authorities.</p>
                
    #             <p>Thank you for your continued commitment to humanitarian aid and disaster relief.</p>
                
    #             <p>Best regards,<br>
    #             Disaster Response Notification System</p>
                
    #             <hr>
    #             <p><small>This is an automated alert system designed to connect NGOs with disaster response opportunities. If you believe you received this message in error, please contact us.</small></p>
    #         </body>
    #         </html>
    #         """,
    #     }

    # resend.Emails.send(params)