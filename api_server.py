"""Simple FastAPI server for the disaster response pipeline UI."""
import json
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from demo import find_disasters, find_ngos, Disaster, NGO, DisasterList, NGOList
from typing import List, Tuple

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def disaster_to_dict(d: Disaster) -> dict:
    return {
        "name": d.name,
        "disaster_type": d.disaster_type.value,
        "severity": d.severity.value,
        "occurred_at": d.occurred_at,
        "location": d.location,
        "country": d.country,
        "region": d.region,
        "latitude": d.latitude,
        "longitude": d.longitude,
        "source_url": d.source_url,
        "source_name": d.source_name,
    }

def ngo_to_dict(n: NGO) -> dict:
    return {
        "name": n.name,
        "contact_email": n.contact_email,
        "phone": n.phone,
        "website": n.website,
        "ngo_type": n.ngo_type.value,
        "aid_type": n.aid_type,
    }

def generate_email_preview(ngo: NGO, disaster: Disaster) -> dict:
    """Generate email preview without sending."""
    return {
        "to": ngo.contact_email,
        "ngo_name": ngo.name,
        "disaster_name": disaster.name,
        "subject": f"Disaster Alert: {disaster.name}",
        "html": f"""
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

<p>Thank you for your continued commitment to humanitarian aid and disaster relief.</p>

<p>Best regards,<br>
Disaster Response Notification System</p>
        """,
    }

async def run_pipeline_stream():
    """Generator that yields pipeline events as SSE."""
    
    # Step 1: Finding disasters
    yield f"data: {json.dumps({'type': 'status', 'step': 'disasters', 'status': 'loading'})}\n\n"
    await asyncio.sleep(0.1)  # Allow event to be sent
    
    disaster_list = await asyncio.to_thread(find_disasters)
    disasters_data = [disaster_to_dict(d) for d in disaster_list.disasters]
    
    yield f"data: {json.dumps({'type': 'disasters', 'data': disasters_data})}\n\n"
    yield f"data: {json.dumps({'type': 'status', 'step': 'disasters', 'status': 'complete'})}\n\n"
    
    # Step 2: Finding NGOs for each disaster
    yield f"data: {json.dumps({'type': 'status', 'step': 'ngos', 'status': 'loading'})}\n\n"
    
    ngo_disaster_list: List[Tuple[NGO, Disaster]] = []
    all_ngo_links = []
    
    for i, disaster in enumerate(disaster_list.disasters):
        yield f"data: {json.dumps({'type': 'ngo_progress', 'disaster_index': i, 'disaster_name': disaster.name})}\n\n"
        await asyncio.sleep(0.1)
        
        ngos = await asyncio.to_thread(find_ngos, disaster)
        ngo_disaster_list.extend([(ngo, disaster) for ngo in ngos.ngos])
        
        for ngo in ngos.ngos:
            all_ngo_links.append({
                "ngo": ngo_to_dict(ngo),
                "disaster_index": i,
                "disaster_name": disaster.name
            })
        
        yield f"data: {json.dumps({'type': 'ngos_found', 'disaster_index': i, 'ngos': [ngo_to_dict(n) for n in ngos.ngos]})}\n\n"
    
    yield f"data: {json.dumps({'type': 'status', 'step': 'ngos', 'status': 'complete'})}\n\n"
    yield f"data: {json.dumps({'type': 'all_ngo_links', 'data': all_ngo_links})}\n\n"
    
    # Step 3: Generate email previews (spoofed - no actual sending)
    yield f"data: {json.dumps({'type': 'status', 'step': 'emails', 'status': 'loading'})}\n\n"
    await asyncio.sleep(0.3)
    
    # Send emails one by one with delay
    total_emails = len(ngo_disaster_list)
    for idx, (ngo, disaster) in enumerate(ngo_disaster_list):
        preview = generate_email_preview(ngo, disaster)
        yield f"data: {json.dumps({'type': 'email_sent', 'index': idx, 'total': total_emails, 'preview': preview})}\n\n"
        await asyncio.sleep(0.4)  # Delay between each email
    
    yield f"data: {json.dumps({'type': 'emails_complete', 'count': total_emails})}\n\n"
    yield f"data: {json.dumps({'type': 'status', 'step': 'emails', 'status': 'complete'})}\n\n"
    yield f"data: {json.dumps({'type': 'pipeline_complete'})}\n\n"

@app.get("/api/run-pipeline")
async def run_pipeline():
    """SSE endpoint to run the pipeline with real-time updates."""
    return StreamingResponse(
        run_pipeline_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@app.get("/api/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
