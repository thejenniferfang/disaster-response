"""Test file for iterating on the find_ngos agent prompt."""
from firecrawl import FirecrawlApp
from pydantic import BaseModel, Field
from typing import List

app = FirecrawlApp(api_key="fc-29a5fd3db63d4b1fb909b232de75a074")

# Schema
class NGO(BaseModel):
    name: str = Field(description="Official name of the NGO")
    contact_email: str = Field(description="Primary contact email address for the NGO")
    phone: str = Field(default="", description="Contact phone number if available")
    website: str = Field(description="NGO website URL")
    aid_type: str = Field(description="Type of aid provided, e.g. 'medical', 'food/water', 'shelter', 'search & rescue', 'general relief'")

class NGOList(BaseModel):
    ngos: List[NGO] = Field(description="List of NGOs")

# Mock disasters for testing
MOCK_DISASTERS = [
    {
        "name": "Turkey-Syria Earthquake",
        "disaster_type": "earthquake",
        "severity": "critical",
        "location": "Gaziantep",
        "country": "Turkey",
        "region": "Southeastern Anatolia",
        "latitude": 37.0662,
        "longitude": 37.3833,
    },
    {
        "name": "California Wildfire",
        "disaster_type": "fire",
        "severity": "high",
        "location": "Los Angeles County",
        "country": "USA",
        "region": "California",
        "latitude": 34.0522,
        "longitude": -118.2437,
    },
    {
        "name": "Bangladesh Flood",
        "disaster_type": "flood",
        "severity": "high",
        "location": "Sylhet",
        "country": "Bangladesh",
        "region": "Sylhet Division",
        "latitude": 24.8949,
        "longitude": 91.8687,
    },
]

# THE PROMPT - edit this to iterate
FIND_NGOS_PROMPT = """
Find 5-10 NGOs that could assist with this disaster: {disaster}

CRITICAL: You MUST find a real contact email for each NGO. Visit their website's contact page to find it.
- Only include NGOs where you can find an actual contact email address
- Skip any NGO if you cannot locate their email
- NO DUPLICATES
"""

def test_find_ngos(disaster_index: int = 0):
    disaster = MOCK_DISASTERS[disaster_index]
    print(f"\n{'='*60}")
    print(f"Testing with: {disaster['name']}")
    print(f"{'='*60}\n")
    
    result = app.agent(
        prompt=FIND_NGOS_PROMPT.format(disaster=disaster),
        schema=NGOList,
        model="spark-1-pro"
    )
    
    print(f"\nResult:\n{result}")
    return result

if __name__ == "__main__":
    # Change index to test different disasters: 0=earthquake, 1=wildfire, 2=flood
    test_find_ngos(0)  # Testing Turkey-Syria earthquake
