from firecrawl import FirecrawlApp
from pydantic import BaseModel, Field
from typing import List, Optional

app = FirecrawlApp(api_key="fc-29a5fd3db63d4b1fb909b232de75a074")

class Disaster(BaseModel):
    name: str = Field(description="")

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