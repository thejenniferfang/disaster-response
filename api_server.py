"""Simple FastAPI server for the disaster response pipeline UI."""
import json
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from demo import find_disasters, find_ngos, send_emails, Disaster, NGO, DisasterList, NGOList
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
    
    # Step 3: Sending emails
    yield f"data: {json.dumps({'type': 'status', 'step': 'emails', 'status': 'loading'})}\n\n"
    await asyncio.sleep(0.1)
    
    email_count = len(ngo_disaster_list)
    email_error = None
    
    if ngo_disaster_list:
        try:
            result = await asyncio.to_thread(send_emails, ngo_disaster_list)
        except Exception as e:
            email_error = str(e)
    
    if email_error:
        yield f"data: {json.dumps({'type': 'emails_sent', 'count': email_count, 'error': email_error})}\n\n"
    else:
        yield f"data: {json.dumps({'type': 'emails_sent', 'count': email_count})}\n\n"
    
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
